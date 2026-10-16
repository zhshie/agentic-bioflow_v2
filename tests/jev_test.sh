#!/bin/bash
# Feature 015 (Jev triage for FAILED runs): the contract in
# specs/015-jev-triage/test-case.md, one block per TC (the id is in a comment).
#
# Nothing here touches the network. The script under test either reads a
# fixture (JEV_DRY_RUN=<dir>) or is handed a fake `curl` / `sleep` on PATH that
# records what it was given. A fake curl that is called in a case that must not
# go online fails the case.
#
# Not here: the real-key replay (scripts/dev/jev_replay.sh against the live
# service) is a manual step (docs/TESTING.md), TC-003/055/062/063/066.
#
# Comparisons "with the base" (hooks/, platform/, the other skills, the golden
# scripts) are not repeated here as byte diffs against a git ref: a permanent
# test that pins other people's files to one commit would turn red the day
# somebody else edits them. The permanent form is "nothing outside the allowed
# files mentions jev.sh" (TC-020/021/024/075).
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
J="$ROOT/scripts/jev.sh"
REPLAY="$ROOT/scripts/dev/jev_replay.sh"
FIX="$ROOT/tests/fixtures/jev"
SPEC="$ROOT/specs/015-jev-triage"
RUNS="$ROOT/skills/runs/SKILL.md"
OPS="$ROOT/skills/operational/SKILL.md"
. "$ROOT/tests/lib/nojq_path.sh"

TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
fails=0
t()    { printf '%-72s ' "$1"; if [ "$2" = "$3" ]; then echo ok; else echo "FAIL: got '$2', wanted '$3'"; fails=$((fails+1)); fi; }
yes_() { printf '%-72s ' "$1"; if [ "$2" = 0 ]; then echo ok; else echo "FAIL"; fails=$((fails+1)); fi; }
has()  { printf '%-72s ' "$1"; if grep -qF -- "$2" <<<"$3"; then echo ok; else echo "FAIL: no '$2'"; fails=$((fails+1)); fi; }
hasnot() { printf '%-72s ' "$1"; if grep -qF -- "$2" <<<"$3"; then echo "FAIL: found '$2'"; fails=$((fails+1)); else echo ok; fi; }
hasre() { printf '%-72s ' "$1"; if grep -qE -- "$2" <<<"$3"; then echo ok; else echo "FAIL: nothing matching '$2'"; fails=$((fails+1)); fi; }

# --- isolated environment ------------------------------------------------------
export HOME="$TMP/home" XDG_CONFIG_HOME="$TMP/home/.config" XDG_STATE_HOME="$TMP/home/.local/state"
export AGENTIC_BIOFLOW_STATE_DIR="$TMP/state"
export LAB_SETTINGS_FILE="$TMP/cfg/env.yaml"
mkdir -p "$HOME" "$TMP/cfg" "$TMP/state"
unset TYPESAFE_API_KEY JEV_ENDPOINT JEV_DRY_RUN JEV_ENABLED JEV_DAILY_CAP JEV_MIN_CONFIDENCE JEV_TODAY JEV_KEY_FILE
KEY="FAKEKEY-9f3a-do-not-print"
STATE="$TMP/state"
reset_state() { rm -rf "$STATE"; mkdir -p "$STATE"; }
enable()  { printf 'jev.enabled: true\n' > "$LAB_SETTINGS_FILE"; }
disable() { rm -f "$LAB_SETTINGS_FILE"; }
mark_seen() { mkdir -p "$STATE"; : > "$STATE/jev-notice-shown"; }

# an err file of N numbered lines
mkerr() { local f="$1" n="$2" i; : > "$f"; for ((i=1;i<=n;i++)); do echo "line $i: samtools: error while loading shared libraries" >> "$f"; done; }
ERR="$TMP/err.txt"; mkerr "$ERR" 5

# --- fakes ---------------------------------------------------------------------
# fake curl: logs argv, stdin, body; answers from $FAKE/seq (one line per request:
# "<http code> <body file>" or "timeout"); the last line repeats.
FAKE="$TMP/fake"; BIN="$TMP/bin"; mkdir -p "$FAKE" "$BIN"
cat > "$BIN/curl" <<'EOF'
#!/bin/bash
F="${FAKE_DIR:?}"
if [ -e "$F/forbid" ]; then : > "$F/CALLED"; echo "fake curl called when it must not be" >&2; exit 99; fi
n=$(( $(cat "$F/n" 2>/dev/null || echo 0) + 1 )); echo "$n" > "$F/n"
printf '%s\n' "$@" > "$F/argv.$n"
cat > "$F/stdin.$n"
out=""; body=""; prev=""
for a in "$@"; do
    case "$prev" in -o) out="$a" ;; --data-binary) body="${a#@}" ;; esac
    prev="$a"
done
[ -n "$body" ] && [ -r "$body" ] && cp "$body" "$F/body.$n"
if [ -n "${FAKE_EVENTS:-}" ]; then echo "curl" >> "$FAKE_EVENTS"; fi
line=$(sed -n "${n}p" "$F/seq"); [ -n "$line" ] || line=$(tail -n 1 "$F/seq")
if [ "$line" = timeout ]; then exit 28; fi
code="${line%% *}"; bodyf="${line#* }"
[ -n "$out" ] && cp "$bodyf" "$out" 2>/dev/null
printf '%s' "$code"
exit 0
EOF
cat > "$BIN/sleep" <<'EOF'
#!/bin/bash
echo "$*" >> "${FAKE_DIR:?}/sleeps"
exit 0
EOF
chmod +x "$BIN/curl" "$BIN/sleep"
fake_reset() { rm -rf "$FAKE"; mkdir -p "$FAKE"; }
fake_seq() { : > "$FAKE/seq"; local s; for s in "$@"; do echo "$s" >> "$FAKE/seq"; done; }
fake_forbid() { fake_reset; : > "$FAKE/forbid"; }
calls() { cat "$FAKE/n" 2>/dev/null || echo 0; }

# run triage; sets OUT (stdout+stderr), RC
J_PATH="$BIN:$PATH"
jev() { OUT=$(env PATH="$J_PATH" FAKE_DIR="$FAKE" "$@" bash "$J" triage --err "$ERR" --exit 1 2>&1); RC=$?; }
jevx() { OUT=$(env PATH="$J_PATH" FAKE_DIR="$FAKE" "$@" 2>&1); RC=$?; }
line1() { sed -n 1p <<<"$OUT"; }
line2() { sed -n 2p <<<"$OUT"; }
machine() { grep -m1 '^JEV status=' <<<"$OUT"; }

# a dry-run dir whose default.json is the named fixture
dry() { local d="$TMP/dry.$$.$RANDOM"; mkdir -p "$d"; cp "$FIX/$1.json" "$d/default.json"; echo "$d"; }

echo "== static: files exist"
for f in scripts/jev.sh scripts/dev/jev_replay.sh docs/adr/0007-jev-optional-triage.md tests/fixtures/jev/high.json; do
    [ -e "$ROOT/$f" ]; yes_ "exists: $f" $?
done
[ -f "$J" ] || { echo "FAIL: scripts/jev.sh is missing, nothing further can run"; exit 1; }

# ===============================================================================
echo "== US1: the triage line"
enable; reset_state; mark_seen; export TYPESAFE_API_KEY="$KEY"
fake_reset
D=$(dry high)
jev JEV_DRY_RUN="$D"
# TC-001
hasre "TC-001 machine line" '^JEV status=ok category=container confidence=0.93 sent_chars=[0-9]+$' "$(line1)"
t     "TC-001 human line"   "$(line2)" "Jev 判斷：container（信心 0.93）"
t     "TC-001 exit 0"       "$RC" 0

# TC-005 / TC-006 / TC-007 -- the script reports; the threshold decision is in the skill and the setting
jev JEV_DRY_RUN="$(dry low)"
hasre "TC-005 low confidence still reported as measured" '^JEV status=ok category=container confidence=0.79 ' "$(line1)"
jev JEV_DRY_RUN="$(dry unknown)"
hasre "TC-006 unknown reported as unknown" '^JEV status=ok category=unknown confidence=0.95 ' "$(line1)"
jev JEV_DRY_RUN="$(dry equal)"
hasre "TC-007 equal-to-threshold reported" '^JEV status=ok category=params confidence=0.80 ' "$(line1)"

# TC-012 empty err
: > "$TMP/empty.txt"
fake_forbid
OUT=$(env PATH="$J_PATH" FAKE_DIR="$FAKE" bash "$J" triage --err "$TMP/empty.txt" --exit 1 2>&1); RC=$?
hasre "TC-012 empty file -> status=empty category=unknown" '^JEV status=empty category=unknown ' "$(line1)"
t     "TC-012 no request made" "$([ -e "$FAKE/CALLED" ] && echo called || echo none)" none
[ -n "$(line2)" ]; yes_ "TC-012 second line explains" $?
t     "TC-012 exit 0" "$RC" 0

# TC-013 only the last 200 lines are sent
fake_reset; fake_seq "200 $FIX/high.json"
mkerr "$TMP/e500.txt" 500; mkerr "$TMP/e1.txt" 1
OUT=$(env PATH="$J_PATH" FAKE_DIR="$FAKE" bash "$J" triage --err "$TMP/e500.txt" --exit 1 2>&1)
sent=$(jq -r '.state.err_tail' "$FAKE/body.1")
t "TC-013 500-line file: err_tail is exactly tail -n 200" "$(printf '%s' "$sent" | sha256sum | cut -c1-64)" "$(tail -n 200 "$TMP/e500.txt" | head -c -1 | sha256sum | cut -c1-64)"
t "TC-013 sent_chars equals the characters sent" "$(machine | sed -n 's/.*sent_chars=\([0-9]*\).*/\1/p')" "$(jq '.state.err_tail|length' "$FAKE/body.1")"
fake_reset; fake_seq "200 $FIX/high.json"
OUT=$(env PATH="$J_PATH" FAKE_DIR="$FAKE" bash "$J" triage --err "$TMP/e1.txt" --exit 1 2>&1)
t "TC-013 1-line file sent whole" "$(jq -r '.state.err_tail' "$FAKE/body.1")" "$(cat "$TMP/e1.txt")"

# TC-014 invalid UTF-8
fake_reset; fake_seq "200 $FIX/high.json"
printf 'ok line\n\xff\xfe broken \xc3\x28 bytes\nlast\n' > "$TMP/bad8.txt"
OUT=$(env PATH="$J_PATH" FAKE_DIR="$FAKE" bash "$J" triage --err "$TMP/bad8.txt" --exit 1 2>&1); RC=$?
jq -e . "$FAKE/body.1" >/dev/null 2>&1; yes_ "TC-014 request body parses as JSON" $?
t "TC-014 body is valid UTF-8" "$(iconv -f UTF-8 -t UTF-8 "$FAKE/body.1" >/dev/null 2>&1 && echo valid || echo invalid)" valid
t "TC-014 exit 0" "$RC" 0

# TC-016 --exit none
fake_reset; fake_seq "200 $FIX/high.json"
OUT=$(env PATH="$J_PATH" FAKE_DIR="$FAKE" bash "$J" triage --err "$ERR" --exit none 2>&1); RC=$?
t "TC-016 state.exit_code is JSON null" "$(jq -c '.state.exit_code' "$FAKE/body.1")" null
hasre "TC-016 still a legal machine line" '^JEV status=ok ' "$(machine)"
fake_reset; fake_seq "200 $FIX/high.json"
OUT=$(env PATH="$J_PATH" FAKE_DIR="$FAKE" bash "$J" triage --err "$ERR" --exit 137 2>&1)
t "TC-016 a number stays a number" "$(jq -c '.state.exit_code' "$FAKE/body.1")" 137

# TC-017 all six statuses have the first-line shape
shape='^JEV status=(ok|disabled|no_key|failed|capped|empty) category=([a-z_]+|-) confidence=([0-9.]+|-) sent_chars=[0-9]+$'
disable; jev JEV_DRY_RUN="$(dry high)"; hasre "TC-017 disabled shape" "$shape" "$(line1)"; t "TC-017 disabled exit" "$RC" 0
enable; (unset TYPESAFE_API_KEY; jev JEV_DRY_RUN="$(dry high)"; hasre "TC-017 no_key shape" "$shape" "$(line1)")
jev JEV_DRY_RUN="$(dry high)"; hasre "TC-017 ok shape" "$shape" "$(line1)"
jev JEV_DRY_RUN="$(dry 500)"; hasre "TC-017 failed shape" "$shape" "$(line1)"

# TC-018 / TC-036 odd answers
for fx in badchoice noconfidence badconfidence; do
    jev JEV_DRY_RUN="$(dry $fx)"
    hasre "TC-018 $fx -> status=failed" '^JEV status=failed ' "$(line1)"
    [ -n "$(line2)" ]; yes_ "TC-018 $fx explains on line 2" $?
    hasnot "TC-018 $fx: the odd category is not echoed as an answer" "category=banana" "$OUT"
done
for fx in malformed nocategory; do
    jev JEV_DRY_RUN="$(dry $fx)"
    hasre "TC-036 $fx -> status=failed" '^JEV status=failed ' "$(line1)"
    t "TC-036 $fx exit 0" "$RC" 0
done

# TC-019 request shape (default endpoint, 8 criteria, only two state fields)
fake_reset; fake_seq "200 $FIX/high.json"
jev
t "TC-019 default endpoint" "$(grep -c '^https://api.typesafe.ai/v1/systemone$' "$FAKE/argv.1")" 1
t "TC-019 model" "$(jq -r .model "$FAKE/body.1")" jev-latest
t "TC-019 state has exactly exit_code and err_tail" "$(jq -c '.state|keys' "$FAKE/body.1")" '["err_tail","exit_code"]'
t "TC-019 eight categories" "$(jq -c '.questions.category.criteria|keys' "$FAKE/body.1")" '["container","input","memory","network","params","tool_bug","unknown","walltime"]'
t "TC-019 a choice question" "$(jq -r '.questions.category.type' "$FAKE/body.1")" choice

# ===============================================================================
echo "== US2: nothing changes when off, keyless, or broken"
# TC-025 / TC-026
disable; reset_state; fake_forbid
jev
t "TC-025 curl never called" "$([ -e "$FAKE/CALLED" ] && echo called || echo none)" none
hasre "TC-025 first line is the machine line" '^JEV status=disabled ' "$(line1)"
t "TC-025 nothing but that line" "$(wc -l <<<"$OUT" | tr -d ' ')" 1
t "TC-025 exit 0" "$RC" 0
printf 'jev.enabled: false\n' > "$LAB_SETTINGS_FILE"; fake_forbid; jev
hasre "TC-026 enabled=false with a key in env" '^JEV status=disabled ' "$(line1)"
t "TC-026 nothing but that line" "$(wc -l <<<"$OUT" | tr -d ' ')" 1
t "TC-026 curl never called" "$([ -e "$FAKE/CALLED" ] && echo called || echo none)" none
t "TC-025 disabled leaves no state behind" "$(ls "$STATE" | wc -l | tr -d ' ')" 0

# TC-028 settings defaults and precedence
S="$ROOT/scripts/settings.sh"
disable
t "TC-028 default enabled"        "$(bash "$S" --jev enabled)" false
t "TC-028 default daily_cap"      "$(bash "$S" --jev daily_cap)" 500
t "TC-028 default min_confidence" "$(bash "$S" --jev min_confidence)" 0.80
printf 'jev.enabled: true\njev.daily_cap: 7\njev.min_confidence: 0.9\n' > "$LAB_SETTINGS_FILE"
t "TC-028 file value enabled"     "$(bash "$S" --jev enabled)" true
t "TC-028 file value daily_cap"   "$(bash "$S" --jev daily_cap)" 7
t "TC-028 file value min_conf"    "$(bash "$S" --jev min_confidence)" 0.9
t "TC-028 env beats the file"     "$(JEV_DAILY_CAP=9 JEV_MIN_CONFIDENCE=0.5 JEV_ENABLED=false bash "$S" --jev daily_cap)" 9
t "TC-028 env beats the file (enabled)" "$(JEV_ENABLED=false bash "$S" --jev enabled)" false

# TC-029 no key
enable; reset_state; mark_seen; fake_forbid
OUT=$(env -u TYPESAFE_API_KEY PATH="$J_PATH" FAKE_DIR="$FAKE" JEV_DRY_RUN="$(dry high)" bash "$J" triage --err "$ERR" --exit 1 2>&1)
hasre "TC-029 no_key" '^JEV status=no_key ' "$(line1)"
has   "TC-029 message" "Jev 已開啟但找不到金鑰，改用原流程" "$(line2)"
t     "TC-029 no request" "$([ -e "$FAKE/CALLED" ] && echo called || echo none)" none

# TC-030 env beats file; file is read from beside the settings file
fake_reset; fake_seq "200 $FIX/high.json"
printf '%s' "FILEKEY-1111" > "$TMP/cfg/.typesafe_key"; chmod 600 "$TMP/cfg/.typesafe_key"
jev TYPESAFE_API_KEY=ENVKEY-2222
has "TC-030 env value used" "Bearer ENVKEY-2222" "$(cat "$FAKE/stdin.1")"
fake_reset; fake_seq "200 $FIX/high.json"
OUT=$(env -u TYPESAFE_API_KEY PATH="$J_PATH" FAKE_DIR="$FAKE" bash "$J" triage --err "$ERR" --exit 1 2>&1)
has "TC-030 file value used when env is absent" "Bearer FILEKEY-1111" "$(cat "$FAKE/stdin.1")"
t "TC-030 jev_key_file() sits beside token_file()" "$(grep -c '^jev_key_file()' "$S")" 1
t "TC-030 same directory rule as token_file" "$(. "$S"; [ "$(dirname "$(token_file)")" = "$(dirname "$(jev_key_file)")" ] && echo same || echo differ)" same

# TC-082 key file readable by others
chmod 644 "$TMP/cfg/.typesafe_key"; fake_forbid
OUT=$(env -u TYPESAFE_API_KEY PATH="$J_PATH" FAKE_DIR="$FAKE" bash "$J" triage --err "$ERR" --exit 1 2>&1); RC=$?
hasre "TC-082 not ok" '^JEV status=(no_key|failed) ' "$(line1)"
has   "TC-082 says what is wrong" "權限" "$(line2)"
hasnot "TC-082 key never printed" "FILEKEY-1111" "$OUT"
t "TC-082 no request" "$([ -e "$FAKE/CALLED" ] && echo called || echo none)" none
t "TC-082 exit 0" "$RC" 0
rm -f "$TMP/cfg/.typesafe_key"

# TC-031 / TC-033 / TC-032 / TC-034 / TC-035 / TC-081 -- with the fake curl
enable; export TYPESAFE_API_KEY="$KEY"; reset_state; mark_seen
fake_reset; fake_seq timeout
jev
hasre "TC-031 timeout -> failed" '^JEV status=failed ' "$(line1)"
has   "TC-031 line 2" "Jev 未回應，改用原流程（原因：timeout）" "$(line2)"
has   "TC-031 curl got --max-time 10" "--max-time
10" "$(cat "$FAKE/argv.1")"
jev JEV_DRY_RUN="$(dry timeout)"
has   "TC-031 dry run timeout fixture" "原因：timeout" "$(line2)"

fake_reset; fake_seq "500 $FIX/malformed.json"
jev
hasre "TC-033 500 -> failed" '^JEV status=failed ' "$(line1)"
has   "TC-033 line 2" "Jev 未回應，改用原流程" "$(line2)"
has   "TC-033 reason carries the code" "500" "$(line2)"
jev JEV_DRY_RUN="$(dry 500)"
has   "TC-033 dry run 500 fixture" "Jev 未回應，改用原流程" "$(line2)"

for code in 401 400; do
    fake_reset; fake_seq "$code $FIX/malformed.json"
    jev
    hasre "TC-032 $code -> failed" '^JEV status=failed ' "$(line1)"
    t     "TC-032 $code: exactly one request" "$(calls)" 1
done

fake_reset; fake_seq "429 $FIX/malformed.json" "200 $FIX/high.json"
reset_state; mark_seen
jev
hasre "TC-034 429 then ok -> ok" '^JEV status=ok category=container ' "$(line1)"
t     "TC-034 two requests" "$(calls)" 2
t     "TC-081 count rises by exactly 1 after 429-then-ok" "$(cat "$STATE"/jev-count-* | tr -d '[:space:]')" 1
jev JEV_DRY_RUN="$(dry 429_then_ok)"
hasre "TC-034 dry run 429_then_ok fixture" '^JEV status=ok ' "$(line1)"

for code in 429 529; do
    fake_reset; fake_seq "$code $FIX/malformed.json"
    reset_state; mark_seen
    jev
    hasre "TC-035 always $code -> failed" '^JEV status=failed ' "$(line1)"
    t     "TC-035 $code: 1 + 2 retries = 3 requests" "$(calls)" 3
    t     "TC-035 $code: waited 1 s then 3 s" "$(tr '\n' ' ' < "$FAKE/sleeps" | sed 's/ *$//')" "1 3"
    t     "TC-081 $code: count rises by at most 1" "$(cat "$STATE"/jev-count-* | tr -d '[:space:]')" 1
done

# TC-037 / TC-038 missing tools
fake_forbid
mkdir -p "$TMP/nocurl"
for f in /usr/bin/* /bin/*; do b=$(basename "$f"); [ "$b" = curl ] && continue; ln -sf "$f" "$TMP/nocurl/$b" 2>/dev/null; done
OUT=$(env PATH="$TMP/nocurl" FAKE_DIR="$FAKE" JEV_DRY_RUN="$(dry high)" /bin/bash "$J" triage --err "$ERR" --exit 1 2>&1); RC=$?
has "TC-037 names curl" "curl" "$OUT"; t "TC-037 exit 0" "$RC" 0
hasre "TC-037 not ok" '^JEV status=failed ' "$(line1)"
NOJQ=$(nojq_path "$TMP") && {
    OUT=$(env PATH="$NOJQ" FAKE_DIR="$FAKE" JEV_DRY_RUN="$(dry high)" /bin/bash "$J" triage --err "$ERR" --exit 1 2>&1); RC=$?
    has "TC-038 names jq" "jq" "$OUT"; t "TC-038 exit 0" "$RC" 0
    hasre "TC-038 not ok" '^JEV status=failed ' "$(line1)"
}

# TC-039 / TC-040 cap
reset_state; mark_seen; echo 500 > "$STATE/jev-count-$(date +%F)"; fake_forbid
jev JEV_DRY_RUN="$(dry high)"
hasre "TC-039 capped" '^JEV status=capped ' "$(line1)"
has   "TC-039 message" "今天的 Jev 次數已用完，改用原流程" "$(line2)"
t     "TC-039 no request" "$([ -e "$FAKE/CALLED" ] && echo called || echo none)" none
reset_state; mark_seen; fake_reset
r=""
for i in 1 2 3; do jev JEV_DRY_RUN="$(dry high)" JEV_DAILY_CAP=2 JEV_TODAY=2030-01-01; r="$r $(line1 | sed 's/^JEV status=\([a-z_]*\) .*/\1/')"; done
t "TC-040 ok ok capped" "${r# }" "ok ok capped"
jev JEV_DRY_RUN="$(dry high)" JEV_DAILY_CAP=2 JEV_TODAY=2030-01-02
hasre "TC-040 next day counts afresh" '^JEV status=ok ' "$(line1)"
t "TC-040 the previous day's count file is gone" "$(ls "$STATE" | grep -c 'jev-count-2030-01-01')" 0

# TC-041 dry run: sha-named fixture first, then default.json
D="$TMP/dryx"; mkdir -p "$D"; cp "$FIX/high.json" "$D/default.json"
SHA=$(tail -n 200 "$ERR" | sha256sum | cut -c1-64)
cp "$FIX/unknown.json" "$D/$SHA.json"
fake_forbid
jev JEV_DRY_RUN="$D"
hasre "TC-041 sha-named fixture wins" '^JEV status=ok category=unknown ' "$(line1)"
rm "$D/$SHA.json"; jev JEV_DRY_RUN="$D"
hasre "TC-041 default.json otherwise" '^JEV status=ok category=container ' "$(line1)"
t "TC-041 no network in dry run" "$([ -e "$FAKE/CALLED" ] && echo called || echo none)" none

# TC-042 the test itself and the runner
t "TC-042 run_all lists jev_test.sh" "$(bash "$ROOT/tests/run_all.sh" --list 2>/dev/null | grep -c 'jev_test.sh')" 1

# TC-043 endpoint override
fake_reset; fake_seq "200 $FIX/high.json"
jev JEV_ENDPOINT=http://127.0.0.1:9/x
t "TC-043 request went to the override" "$(grep -c '^http://127.0.0.1:9/x$' "$FAKE/argv.1")" 1
t "TC-043 model unchanged" "$(jq -r .model "$FAKE/body.1")" jev-latest

# TC-023 only one destination, no fallback after failure
fake_reset; fake_seq "500 $FIX/malformed.json"
jev
t "TC-023 after a 500 only the one endpoint was contacted" "$(cat "$FAKE"/argv.* | grep -E '^https?://' | sort -u | wc -l | tr -d ' ')" 1

# ===============================================================================
echo "== US3: what is sent, and the key"
# TC-045 .. TC-048
reset_state; fake_reset; fake_seq "200 $FIX/high.json"
EV="$TMP/events"; : > "$EV"
OUT=$(env PATH="$J_PATH" FAKE_DIR="$FAKE" FAKE_EVENTS="$EV" bash "$J" triage --err "$ERR" --exit 1 2>&1); RC=$?
for w in "200" "exit code" "api.typesafe.ai" "樣本" "不保留" "jev.enabled"; do has "TC-045 notice mentions: $w" "$w" "$OUT"; done
t "TC-047 curl was called after the notice was out" "$(wc -l < "$EV" | tr -d ' ')" 1
fake_reset; fake_seq "200 $FIX/high.json"
jev
hasnot "TC-046 second run: no notice" "api.typesafe.ai" "$OUT"
hasre  "TC-046 second run: first line is the machine line" '^JEV status=ok ' "$(line1)"
# TC-047 order: notice text comes before anything curl wrote
reset_state; fake_reset; fake_seq "200 $FIX/high.json"
OUT=$(env PATH="$J_PATH" FAKE_DIR="$FAKE" bash "$J" triage --err "$ERR" --exit 1 2>&1)
first=$(grep -n 'api.typesafe.ai' <<<"$OUT" | head -1 | cut -d: -f1); mach=$(grep -n '^JEV status=' <<<"$OUT" | head -1 | cut -d: -f1)
[ -n "$first" ] && [ -n "$mach" ] && [ "$first" -lt "$mach" ]; yes_ "TC-047 notice precedes the result" $?
# TC-048 nothing sent -> no notice, no marker
reset_state; disable; jev JEV_DRY_RUN="$(dry high)"
hasnot "TC-048 disabled: no notice" "api.typesafe.ai" "$OUT"
t "TC-048 disabled: no marker" "$(ls "$STATE" | wc -l | tr -d ' ')" 0
enable; reset_state
OUT=$(env -u TYPESAFE_API_KEY PATH="$J_PATH" FAKE_DIR="$FAKE" JEV_DRY_RUN="$(dry high)" bash "$J" triage --err "$ERR" --exit 1 2>&1)
hasnot "TC-048 no key: no notice" "api.typesafe.ai" "$OUT"
t "TC-048 no key: no marker" "$(ls "$STATE" | grep -c notice)" 0

# TC-049 / TC-050 / TC-084 / TC-052 the key goes nowhere visible
reset_state; export TYPESAFE_API_KEY="$KEY"
ALL=""
fake_reset; fake_seq "200 $FIX/high.json"; jev;                  ALL="$ALL$OUT"
fake_reset; fake_seq "500 $FIX/malformed.json"; jev;             ALL="$ALL$OUT"
jev JEV_DRY_RUN="$(dry high)";                                    ALL="$ALL$OUT"
disable; jev JEV_DRY_RUN="$(dry high)";                           ALL="$ALL$OUT"; enable
reset_state; echo 500 > "$STATE/jev-count-$(date +%F)"; jev JEV_DRY_RUN="$(dry high)"; ALL="$ALL$OUT"
OUT=$(env -u TYPESAFE_API_KEY PATH="$J_PATH" FAKE_DIR="$FAKE" JEV_DRY_RUN="$(dry high)" bash "$J" triage --err "$ERR" --exit 1 2>&1); ALL="$ALL$OUT"
OUT=$(env PATH="$J_PATH" FAKE_DIR="$FAKE" bash "$J" triage --err "$TMP/empty.txt" --exit 1 2>&1); ALL="$ALL$OUT"
hasnot "TC-049 the key is in no output of any status" "$KEY" "$ALL"
fake_reset; fake_seq "200 $FIX/high.json"; reset_state; jev
hasnot "TC-050 key not on curl's argument list" "$KEY" "$(cat "$FAKE/argv.1")"
has    "TC-084 --config is passed" "--config" "$(cat "$FAKE/argv.1")"
t      "TC-084 and it reads stdin ('-')" "$(grep -A1 -x -- '--config' "$FAKE/argv.1" | tail -1)" "-"
has    "TC-084 stdin carries the header line" "header = \"Authorization: Bearer $KEY\"" "$(cat "$FAKE/stdin.1")"
hasnot "TC-052 key not in the state dir" "$KEY" "$(cat "$STATE"/* 2>/dev/null)"
hasnot "TC-052 key not in the body sent" "$KEY" "$(cat "$FAKE/body.1")"
# TC-070 only the counter and the marker are written
reset_state; fake_reset; fake_seq "200 $FIX/high.json"; jev
t "TC-070 state dir holds only a counter and a marker" "$(ls "$STATE" | sed 's/[0-9-]\{10\}$//' | sort | tr '\n' ' ')" "jev-count- jev-notice-shown "
t "TC-069 counter is one integer" "$(cat "$STATE"/jev-count-* | tr -d '[:space:]')" 1
t "TC-069 marker is empty" "$(wc -c < "$STATE/jev-notice-shown" | tr -d ' ')" 0
# TC-044 nothing in the repo
t "TC-044 no repo file changed or added by running it" "$(git -C "$ROOT" status --porcelain -- . ':!tests' ':!scripts' ':!skills' ':!docs' ':!specs' ':!CHANGELOG.md' ':!.gitignore' 2>/dev/null | wc -l | tr -d ' ')" 0

# TC-074 every non-ok path says something a person can read
echo "== VI-13: no quiet pass"
for k in empty capped nokey failed; do
    case "$k" in
        empty)  reset_state; mark_seen; OUT=$(env PATH="$J_PATH" FAKE_DIR="$FAKE" bash "$J" triage --err "$TMP/empty.txt" --exit 1 2>&1) ;;
        capped) reset_state; mark_seen; echo 500 > "$STATE/jev-count-$(date +%F)"; jev JEV_DRY_RUN="$(dry high)" ;;
        nokey)  reset_state; OUT=$(env -u TYPESAFE_API_KEY PATH="$J_PATH" FAKE_DIR="$FAKE" JEV_DRY_RUN="$(dry high)" bash "$J" triage --err "$ERR" --exit 1 2>&1) ;;
        failed) reset_state; mark_seen; jev JEV_DRY_RUN="$(dry 500)" ;;
    esac
    hasnot "TC-074 $k is not reported as ok" "status=ok" "$(line1)"
    [ -n "$(line2)" ]; yes_ "TC-074 $k says something on line 2" $?
    has "TC-074 $k says what happens next" "原流程" "$(line2)"
done
has "TC-074 missing curl says so" "原流程" "$(env PATH="$TMP/nocurl" JEV_DRY_RUN="$(dry high)" /bin/bash "$J" triage --err "$ERR" --exit 1 2>&1)"

# TC-022 the script only prints; nothing is executed from a response
echo "== static: what the script does"
code=$(grep -vE '^[[:space:]]*#' "$J")
printf '%-72s ' "TC-022 no eval, no bash -c, no tw/sbatch/scancel"
if grep -nE '(^|[^[:alnum:]_])(eval|sbatch|scancel|squeue)([^[:alnum:]_]|$)|bash[[:space:]]+-c|(^|[|;&(][[:space:]]*)tw[[:space:]]' <<<"$code" >/dev/null; then echo FAIL; fails=$((fails+1)); else echo ok; fi
printf '%-72s ' "TC-022 rm only touches the script's own jev-count files"
badrm=$(grep -nE '(^|[^[:alnum:]_])rm[[:space:]]' <<<"$code" | grep -vE 'jev-count|\$\{?(body|resp|tail|tmp|work|cfg|TMPD|TMP_?DIR|tmpd)' || true)
if [ -n "$badrm" ]; then echo "FAIL: $badrm"; fails=$((fails+1)); else echo ok; fi
# TC-068 headers
for f in "$J" "$REPLAY"; do
    printf '%-72s ' "TC-068 $(basename "$f") names its alternative"
    if sed -n 1,40p "$f" | grep -qE '^#[[:space:]]*(Not[[:space:]]+.+:|Nothing existing:)'; then echo ok; else echo FAIL; fails=$((fails+1)); fi
done
t "TC-071 no personal paths in jev.sh" "$(grep -cE '/(home|work|scratch|lustre)/[A-Za-z]' "$J")" 0

# ===============================================================================
echo "== skills: where the call sits (TC-002/004/008/009/010/011/015/076/078)"
runs=$(cat "$RUNS"); ops=$(cat "$OPS")
lno() { grep -nF -- "$1" "$2" | head -1 | cut -d: -f1; }
l_nore=$(lno 'No refusal lines up' "$RUNS"); l_137=$(lno '137, or killed' "$RUNS"); l_nolog=$(lno 'No `.command.log`' "$RUNS")
l_jev=$(lno 'scripts/jev.sh triage --err' "$RUNS"); l_any=$(lno '**Anything else.**' "$RUNS"); l_foot=$(lno 'On a site with unrestricted egress' "$RUNS")
[ -n "$l_jev" ] && [ "$l_nore" -lt "$l_137" ] && [ "$l_137" -lt "$l_nolog" ] && [ "$l_nolog" -lt "$l_jev" ] && [ "$l_jev" -lt "$l_any" ] && [ "$l_any" -lt "$l_foot" ]
yes_ "TC-002 Jev step sits inside 'No refusal lines up', after 137 and no-log, before 'Anything else'" $?
has  "TC-002 the call is a plain script call with --exit" "--exit" "$(sed -n "${l_jev:-1}p" "$RUNS")"
o_egress=$(lno 'egress log' "$OPS"); o_jev=$(lno 'jev.sh triage' "$OPS"); o_only=$(lno '**Only then**' "$OPS")
[ -n "$o_jev" ] && [ -n "$o_egress" ] && [ "$o_egress" -lt "$o_jev" ]
yes_ "TC-002 operational/SKILL.md order puts Jev after the egress check" $?
has  "TC-002 operational: after the 137 and missing-log rules" "137" "$(sed -n "$((${o_jev:-5}-4)),${o_jev:-5}p" "$OPS")"

# TC-004 categories
cats="memory walltime network container input params tool_bug unknown"
for c in $cats; do has "TC-004 jev.sh sends category $c" "$c" "$(cat "$J")"; done
for c in walltime network container input params tool_bug; do
    sec=$(awk -v c="$c" '$0 ~ "^#### `"c"`" {p=1; next} /^#### |^### |^## / {p=0} p' "$RUNS")
    [ -n "$sec" ]; yes_ "TC-004 SKILL.md has a section for $c" $?
    has "TC-004 $c: what to look at first" "Look first" "$sec"
    has "TC-004 $c: the usual fix" "Usual fix" "$sec"
    has "TC-004 $c: when to ask" "Ask the user" "$sec"
done
has "TC-004 memory points at the existing Out of memory section" "Out of memory" "$(grep -i 'memory' "$RUNS" | grep -i jev)"

# TC-005..007, TC-015, TC-008, TC-076, TC-078
jevtop=$(lno "Jev triage, only if the user turned it on" "$RUNS"); jevblock=$(sed -n "${jevtop:-1},$((${l_any:-2}-1))p" "$RUNS")
jevsec=$(awk '/^### Jev categories/{p=1} /^### Out of memory/{p=0} p' "$RUNS")
all="$jevblock
$jevsec"
has "TC-005 low confidence is reported" "Jev 沒把握，照原流程" "$all"
has "TC-005 and goes to Anything else" "Anything else" "$jevblock"
has "TC-007 the threshold is jev.min_confidence, equal counts" "jev.min_confidence" "$all"
hasre "TC-007 equal to the threshold counts as sure" 'equal|at least|>=|≥' "$all"
has "TC-006 unknown goes to the original flow" "unknown" "$jevblock"
has "TC-001 report line shape" "Jev 判斷：" "$jevblock"
hasre "TC-015 only the first failing task, once" 'first failing task' "$jevblock"
has "TC-008 Jev decides nothing that needs consent" "Jev 的判斷不讓任何需要使用者同意的事變成自動" "$all"
for base_line in 'It is not on that list.** ⏸' '⏸ Stop and ask only if the fix turns out to need a pipeline parameter'; do
    has "TC-008 existing ⏸ line kept: ${base_line:0:40}" "$base_line" "$runs"
done
has "TC-076 params category stops for the user" "⏸" "$(awk '/^#### `params`/{p=1;next} /^#### |^### /{p=0} p' "$RUNS")"
has "TC-076 network category stops for the user" "⏸" "$(awk '/^#### `network`/{p=1;next} /^#### |^### /{p=0} p' "$RUNS")"
has "TC-078 the machine line is for the skill, never shown" "never show" "$jevblock"
has "TC-078 disabled: the user sees nothing new" "disabled" "$jevblock"
has "TC-009 refusal branch is untouched: egress before Jev" "scripts/on_site.sh --script scripts/egress_ctl.sh denied" "$runs"
[ "$(lno 'scripts/egress_ctl.sh denied' "$RUNS")" -lt "$l_jev" ]; yes_ "TC-009/010/011 Jev comes after the egress, 137 and no-log rules" $?
# TC-060 the five rule-handled items
LBL="$SPEC/labels.json"
t "TC-060 T01 T03 T05 T43 are exit 137" "$(jq -r '[.[]|select(.id=="T01" or .id=="T03" or .id=="T05" or .id=="T43")|.exit_code]|unique|tostring' "$LBL")" "[137]"
has "TC-060 T14 is a refusal line" "DENY-DOMAIN" "$(jq -r '.[]|select(.id=="T14")|.err_tail' "$LBL")"
t "TC-060 no other item is 137 or a refusal" "$(jq -r '[.[]|select(.id!="T01" and .id!="T03" and .id!="T05" and .id!="T43" and .id!="T14")|select(.exit_code==137 or (.err_tail|test("DENY-DOMAIN")))]|length' "$LBL")" 0

# ===============================================================================
echo "== scope: who may mention jev.sh (TC-020/021/024/075/085)"
refs=$(cd "$ROOT" && git ls-files 2>/dev/null | grep -vE '^(specs/|tests/|docs/|CHANGELOG\.md|\.gitignore)' | xargs grep -lI 'jev' 2>/dev/null | sort | tr '\n' ' ')
t "TC-020 only these non-doc files mention jev" "$refs" "scripts/dev/jev_replay.sh scripts/jev.sh scripts/settings.sh skills/operational/SKILL.md skills/runs/SKILL.md "
t "TC-085 nothing under platform/ mentions jev" "$(grep -rli jev "$ROOT/platform" 2>/dev/null | wc -l | tr -d ' ')" 0
t "TC-075 hooks/ do not mention jev" "$(grep -rli jev "$ROOT/hooks" 2>/dev/null | wc -l | tr -d ' ')" 0
t "TC-021 task_health.sh and report.sh do not mention jev" "$(grep -li jev "$ROOT/scripts/task_health.sh" "$ROOT/scripts/report.sh" 2>/dev/null | wc -l | tr -d ' ')" 0
t "TC-027 the FAILED-flow scripts do not mention jev" "$(grep -li jev "$ROOT/scripts/egress_ctl.sh" "$ROOT/scripts/on_site.sh" "$ROOT/scripts/task_health.sh" "$ROOT/scripts/report.sh" 2>/dev/null | wc -l | tr -d ' ')" 0
has "TC-085 Constitution Check says it is not an action-layer tool" "not an MCP tool" "$(cat "$SPEC/plan.md")"
has "TC-085 ... and not part of the action layer" "not part of the action layer" "$(cat "$SPEC/plan.md")"

# ===============================================================================
echo "== docs (TC-053/054/056/057/079/083/088, TC-059/065)"
sd=$(cat "$ROOT/docs/SETTINGS.md")
for w in 'jev.enabled' '.typesafe_key' 'TYPESAFE_API_KEY' 'jev.daily_cap' 'jev.min_confidence' 'JEV_ENDPOINT' 'jev-count-' 'err_tail'; do
    has "TC-053 SETTINGS.md mentions $w" "$w" "$sd"
done
has "TC-079 spec has FR-012 with jev.min_confidence" "FR-012" "$(grep FR-012 "$SPEC/spec.md")"
has "TC-079 ... and the key" "jev.min_confidence" "$(grep FR-012 "$SPEC/spec.md")"
adr="$ROOT/docs/adr/0007-jev-optional-triage.md"
for w in '只要有價值就設計，若有風險未來考慮變成本地端' '使用者自備' '只做除錯' 'docs.typesafe.ai'; do has "TC-054 ADR quotes: $w" "$w" "$(cat "$adr" 2>/dev/null)"; done
hasnot "TC-054 no ❌ Jev left in POSITIONING" "❌ Jev" "$(cat "$ROOT/docs/POSITIONING.md")"
has "TC-054 POSITIONING says optional, off by default" "預設關" "$(grep -i 'jev' "$ROOT/docs/POSITIONING.md")"
has "TC-054 POSITIONING links the ADR" "0007" "$(grep -i 'jev' "$ROOT/docs/POSITIONING.md")"
t "TC-054 exactly one ADR 0007" "$(ls "$ROOT"/docs/adr/0007-* | wc -l | tr -d ' ')" 1
t "TC-056 plugin.json still 3.0.0-dev" "$(jq -r .version "$ROOT/.claude-plugin/plugin.json")" "3.0.0-dev"
t "TC-056 CHANGELOG has exactly one Jev line" "$(grep -ci jev "$ROOT/CHANGELOG.md")" 1
has "TC-056 spec FR-011 says CHANGELOG" "CHANGELOG.md" "$(grep FR-011 "$SPEC/spec.md")"
has "TC-056 tasks T013 says CHANGELOG" "CHANGELOG.md" "$(grep T013 "$SPEC/tasks.md")"
t "TC-057 no jev.enabled: true shipped in configs/ or examples" "$(grep -rIl 'jev.enabled:[[:space:]]*true' "$ROOT/configs" "$ROOT/scripts" "$ROOT/skills" "$ROOT/hooks" 2>/dev/null | wc -l | tr -d ' ')" 0
t "TC-057 no TypeSafe key in the repo" "$(cd "$ROOT" && git ls-files | grep -v '^tests/jev_test.sh$' | xargs grep -lIE 'typesafe[^ ]*[:=][[:space:]]*["'"'"']?[A-Za-z0-9]{24,}' 2>/dev/null | wc -l | tr -d ' ')" 0
t "TC-059 labels.json: 42 items" "$(jq length "$LBL")" 42
t "TC-059 labels.json: the approved ids" "$(jq -r '[.[].id]|join(" ")' "$LBL")" "$(for i in $(seq 1 28) $(seq 30 40) 42 43 44; do printf 'T%02d ' "$i"; done | sed 's/ $//')"
t "TC-059 labels.json: byte-identical to the approved file" "$(sha256sum "$LBL" | cut -c1-64)" dd1b455b2f4ef0c7cf0c3d6940a5e092d44abb6d3b1592f8e94528260fc83e57
t "TC-088 no old slug path in spec, plan, tasks" "$(grep -l "specs/009-jev-triage" "$SPEC/spec.md" "$SPEC/plan.md" "$SPEC/tasks.md" | wc -l | tr -d " ")" 0
t "TC-088 no pointer to the old command file" "$(grep -l 'commands/runs.md' "$SPEC/spec.md" "$SPEC/plan.md" "$SPEC/tasks.md" | wc -l | tr -d ' ')" 0
t "TC-088 old spec folder is absent" "$([ -e "$ROOT/specs/009-jev-triage" ] && echo there || echo absent)" absent
# TC-083 the documented creation command makes a mode-600 key file
cmd=$(grep -F "umask 077; printf '%s' " "$ROOT/docs/SETTINGS.md" | head -1 | sed 's/^[[:space:]`]*//; s/`[[:space:]]*$//')
[ -n "$cmd" ]; yes_ "TC-083 SETTINGS.md gives the creation command" $?
if [ -n "$cmd" ]; then
    d="$TMP/keydir"; mkdir -p "$d"
    run_cmd=${cmd//<settings dir>/$d}; run_cmd=${run_cmd//\"\$KEY\"/\"\$KEY\"}
    ( KEY="$KEY"; eval "$run_cmd" ) 2>/dev/null
    t "TC-083 the file is mode 600" "$(stat -c %a "$d/.typesafe_key" 2>/dev/null)" 600
    t "TC-083 and holds the key" "$(cat "$d/.typesafe_key" 2>/dev/null)" "$KEY"
fi
t "TC-083 jev.sh never creates a key file" "$(grep -cE '>[[:space:]]*"?[^ ]*typesafe_key|jev_key_file\)?"?[[:space:]]*>' "$J")" 0
# TC-065 only with a passing report may the docs say 建議開啟
rep="$SPEC/replay-report.md"
rec=$(cd "$ROOT" && git ls-files docs skills | xargs grep -l '建議開啟' 2>/dev/null | wc -l | tr -d ' ')
if [ "$rec" -gt 0 ]; then
    ok=$(sed -n 's/.*答對率[^0-9]*\([0-9]*\)\/37.*/\1/p' "$rep" 2>/dev/null | head -1)
    [ -n "$ok" ] && [ "$ok" -ge 34 ]; yes_ "TC-065 '建議開啟' needs a report with >= 34/37" $?
else
    t "TC-065 no '建議開啟' without a passing report" 0 0
fi

# ===============================================================================
echo "== US4: the approved question bank (TC-058, TC-060, TC-061, TC-064, TC-067, TC-080)"
# every item through jev.sh under JEV_DRY_RUN, one fixture per item (named by the sha of its tail)
BD="$TMP/bank"; mkdir -p "$BD"; unset TYPESAFE_API_KEY; export TYPESAFE_API_KEY="$KEY"
enable; reset_state; mark_seen
n_ok=0; n_all=0
while IFS=$'\t' read -r id code label; do
    f="$TMP/q.$id.txt"; jq -r --arg id "$id" '.[]|select(.id==$id)|.err_tail' "$LBL" > "$f"
    sha=$(tail -n 200 "$f" | sha256sum | cut -c1-64)
    jq -cn --arg c "$label" '{answers:{category:{choice:$c,confidence:0.95}}}' > "$BD/$sha.json"
    ex=$code; [ "$code" = null ] && ex=none
    o=$(env PATH="$J_PATH" FAKE_DIR="$FAKE" JEV_DRY_RUN="$BD" JEV_DAILY_CAP=1000 bash "$J" triage --err "$f" --exit "$ex" 2>&1)
    n_all=$((n_all+1))
    grep -qE "^JEV status=ok category=$label confidence=0.95 " <<<"$o" && n_ok=$((n_ok+1))
done < <(jq -r '.[]|[.id, (.exit_code|tostring), .label]|@tsv' "$LBL")
t "TC-058 all 42 items run to status=ok with their category" "$n_ok/$n_all" "42/42"

# TC-061 the replay refuses without a key
env -u TYPESAFE_API_KEY PATH="$J_PATH" bash "$REPLAY" >"$TMP/r61.out" 2>&1; rc61=$?
[ "$rc61" != 0 ]; yes_ "TC-061 replay without key or dry run exits non-zero" $?
has "TC-061 and says a key is needed" "TYPESAFE_API_KEY" "$(cat "$TMP/r61.out")"
t   "TC-061 and writes no report" "$([ -e "$SPEC/replay-report.md" ] && echo wrote || echo none)" none

# TC-064 offline replay with 5 wrong answers: 32/37
RD="$TMP/replay"; mkdir -p "$RD"
cats8=(memory walltime network container input params tool_bug unknown)
wrong=0; wrongids=""
while IFS=$'\t' read -r id label; do
    f="$TMP/q.$id.txt"; sha=$(tail -n 200 "$f" | sha256sum | cut -c1-64)
    ans="$label"
    case "$id" in T02|T04|T06|T07|T08) ans=$([ "$label" = unknown ] && echo memory || echo unknown); wrongids="$wrongids $id" ;; esac
    jq -cn --arg c "$ans" '{answers:{category:{choice:$c,confidence:0.95}}}' > "$RD/$sha.json"
done < <(jq -r '.[]|[.id,.label]|@tsv' "$LBL")
OUT=$(env PATH="$J_PATH" TYPESAFE_API_KEY="$KEY" JEV_DRY_RUN="$RD" JEV_DAILY_CAP=1000 JEV_TODAY=2031-01-01 bash "$REPLAY" 2>&1); RC=$?
t   "TC-064 the offline replay runs to the end" "$RC" 0
has "TC-064 reports 32/37" "32/37" "$OUT"
for id in T02 T04 T06 T07 T08; do has "TC-064 lists wrong id $id" "$id" "$(grep -i '答錯' <<<"$OUT")"; done
hasnot "TC-064/065 no recommendation to switch on at 86%" "建議開啟" "$OUT"
# TC-080 both read-size columns, and no skipped item is scored
for id in T01 T03 T05 T14 T43; do hasnot "TC-063 $id is not scored" "| $id |" "$(grep -E '^\| T[0-9]+ ' <<<"$OUT" | grep -F "| $id |")"; done
t   "TC-080 37 scored rows" "$(grep -cE '^\| T[0-9]+ ' <<<"$OUT")" 37
has "TC-080 column: with Jev" "有 Jev" "$OUT"
has "TC-080 column: without Jev" "沒有 Jev" "$OUT"
rowT04=$(grep -E '^\| T04 ' <<<"$OUT")
w=$(awk -F'|' '{gsub(/ /,"",$0); print $0}' <<<"$rowT04")
expect_len=$(jq -r '.[]|select(.id=="T04")|.err_tail' "$LBL" | tail -n 200 | jq -Rs 'length')
hasre "TC-080 the with-Jev figure is computed from the bank (T04: $expect_len)" "(^|[^0-9])$expect_len([^0-9]|$)" "$rowT04"
t   "TC-080 with-Jev never exceeds without-Jev" "$(grep -E '^\| T[0-9]+ ' <<<"$OUT" | awk -F'|' '{ if (($(NF-2)+0) > ($(NF-1)+0)) bad++ } END{print bad+0}')" 0
has "TC-080 totals row" "總計" "$OUT"
# the 5 skipped items are said to be skipped
has "TC-063 the report says the five were never sent to Jev" "T01" "$(grep -iE '不呼叫|沒有呼叫|not called' <<<"$OUT")"

# TC-067 fixture coverage
for fx in high low unknown 500 timeout 429_then_ok; do [ -f "$FIX/$fx.json" ]; yes_ "TC-067 fixture $fx exists" $?; done
t "TC-067 the missing-jq, no-key and capped cases are in this file" "$(grep -c 'TC-038\|TC-029\|TC-039' "$ROOT/tests/jev_test.sh" | awk '{print ($1>=3)?"yes":"no"}')" yes

# TC-042 this file never reaches the network by itself
printf '%-72s ' "TC-042 every triage call is dry-run or goes through the fake curl"
if grep -nE 'curl[[:space:]]+(-[A-Za-z-]+[[:space:]]+)*https?://' "$ROOT/tests/jev_test.sh" | grep -v '^[0-9]*:#' | grep -vE 'FAKE|argv|grep|has|\^http' >/dev/null; then echo FAIL; fails=$((fails+1)); else echo ok; fi

echo
if [ "$fails" -gt 0 ]; then echo "FAIL: $fails check(s) failed in jev_test.sh"; exit 1; fi
echo "OK: jev triage contract holds"
