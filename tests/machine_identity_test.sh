#!/bin/bash
# Feature 006 (specs/006-machine-identity): "this machine" is a random id kept
# in the user's own config area, not hostname + `uname -s`. Covers TC-001..TC-013.
# A fake `uname` on PATH answers -n / -s from FAKE_N / FAKE_S, which is how a
# Windows update (new build number) or a renamed host is simulated.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SETTINGS="$ROOT/scripts/settings.sh"
PROOF="$ROOT/scripts/setup_proof.sh"
WHERE="$ROOT/scripts/where.sh"
TMP=$(mktemp -d); trap 'chmod -R u+rwx "$TMP" 2>/dev/null; rm -rf "$TMP"' EXIT
fails=0

t()      { printf '%-66s ' "$1"; [ "$2" = "$3" ] && echo ok || { echo "FAIL: got '$2', wanted '$3'"; fails=$((fails+1)); }; }
has()    { printf '%-66s ' "$1"; grep -qF -- "$2" <<<"$3" && echo ok || { echo "FAIL: lacks '$2' <<$3>>"; fails=$((fails+1)); }; }
hasnot() { printf '%-66s ' "$1"; grep -qF -- "$2" <<<"$3" && { echo "FAIL: found '$2'"; fails=$((fails+1)); } || echo ok; }
exists() { [ -e "$1" ] && echo yes || echo no; }

UB="$TMP/ubin"; mkdir -p "$UB"
cat > "$UB/uname" <<'EOF'
#!/bin/sh
case "${1:-}" in
    -n) printf '%s\n' "${FAKE_N:-testhost}" ;;
    -s) printf '%s\n' "${FAKE_S:-Linux}" ;;
    *)  exit 1 ;;
esac
EOF
chmod +x "$UB/uname"

cat > "$UB/tw" <<'EOF'
#!/bin/bash
case "$*" in *"runs list"*) cat "$RUNS_LIST_FILE" ;; *) exit 1 ;; esac
EOF
chmod +x "$UB/tw"

# A fresh fixture per case: settings root, machines dir, and a home.
CFG=""; MD=""; HM=""; n=0
fresh() {
    n=$((n+1))
    CFG="$TMP/c$n/config"; MD="$CFG/machines"; HM="$TMP/h$n"
    mkdir -p "$CFG" "$HM"
    printf 'workspace_id: 999\nseqera_user: alice\n' > "$CFG/env.yaml"
    chmod 600 "$CFG/env.yaml"
}
# run <home> <FAKE_N> <FAKE_S> -- cmd...   (settings root via LAB_SETTINGS_FILE)
run() {
    local h="$1" fn="$2" fs="$3"; shift 4
    env -u XDG_CONFIG_HOME -u LAB_RUNS_DIR -u SEQERA_TOKEN_FILE -u TOWER_ACCESS_TOKEN \
        HOME="$h" PATH="$UB:$PATH" FAKE_N="$fn" FAKE_S="$fs" \
        LAB_SETTINGS_FILE="$CFG/env.yaml" "$@"
}
IDF() { echo "$1/.config/agentic-bioflow/machine-id"; }
# a pre-006 machine file for the given fake host/system
legacy() { # legacy <host> <system> <content>
    mkdir -p "$MD"; printf '%s\n' "$3" > "$MD/$1-$2.yaml"
}

# --- TC-001: first write generates the id and uses it -----------------------
fresh
out=$(run "$HM" boxa Linux -- bash "$SETTINGS" --set tw_bin /x/tw 2>&1); rc=$?
t "TC-001 --set exits 0" "$rc" "0"
id="$(head -1 "$(IDF "$HM")" 2>/dev/null)"
t "TC-001 id file is hostname-8hex" "$(printf '%s' "$id" | grep -cE '^boxa-[0-9a-f]{8}$')" "1"
t "TC-001 machine file is machines/<id>.yaml" "$(exists "$MD/$id.yaml")" "yes"
t "TC-001 it holds tw_bin" "$(grep -c '^tw_bin: /x/tw$' "$MD/$id.yaml" 2>/dev/null)" "1"
t "TC-001 no hostname-system named file" "$(exists "$MD/boxa-Linux.yaml")" "no"
t "TC-001 only one machine file" "$(ls "$MD" | wc -l | tr -d ' ')" "1"

# --- TC-002: renamed host / new build, same value ---------------------------
t "TC-002 same value after uname change" \
  "$(run "$HM" otherbox MINGW64_NT-10.0-26200 -- bash "$SETTINGS" tw_bin)" "/x/tw"
t "TC-002 machine_id() still the stored id" \
  "$(run "$HM" otherbox MINGW64_NT-10.0-26200 -- bash -c ". '$SETTINGS' >/dev/null 2>&1; machine_id")" "$id"

# --- TC-003: reading creates nothing ----------------------------------------
fresh
run "$HM" boxa Linux -- bash -c ". '$SETTINGS'; setting tw_bin; setting workspace_id; machine_id" >/dev/null 2>&1
run "$HM" boxa Linux -- bash "$SETTINGS" tw_bin >/dev/null 2>&1
run "$HM" boxa Linux -- bash "$SETTINGS" --summary >/dev/null 2>&1
t "TC-003 no id file after reading" "$(exists "$(IDF "$HM")")" "no"
t "TC-003 no machines dir after reading" "$(exists "$MD")" "no"
t "TC-003 nothing at all under HOME" "$(find "$HM" -type f | wc -l | tr -d ' ')" "0"

# --- TC-004: legacy file read without an id ---------------------------------
fresh; legacy boxa Linux "tw_bin: /old/tw"
t "TC-004 reads the legacy file's value" "$(run "$HM" boxa Linux -- bash "$SETTINGS" tw_bin)" "/old/tw"
t "TC-004 reading did not create an id" "$(exists "$(IDF "$HM")")" "no"
t "TC-004 reading did not rename it" "$(exists "$MD/boxa-Linux.yaml")" "yes"

# --- TC-005: first write renames the legacy file ----------------------------
run "$HM" boxa Linux -- bash "$SETTINGS" --set site_bridge wsl >/dev/null 2>&1
id="$(head -1 "$(IDF "$HM")" 2>/dev/null)"
t "TC-005 legacy name is gone" "$(exists "$MD/boxa-Linux.yaml")" "no"
t "TC-005 renamed to <id>.yaml" "$(exists "$MD/$id.yaml")" "yes"
t "TC-005 old value kept" "$(run "$HM" boxa Linux -- bash "$SETTINGS" tw_bin)" "/old/tw"
t "TC-005 new value written" "$(run "$HM" boxa Linux -- bash "$SETTINGS" site_bridge)" "wsl"
t "TC-005 exactly one machine file" "$(ls "$MD" | wc -l | tr -d ' ')" "1"

# --- acceptance HIGH-1: the id already exists (made in ANOTHER root, e.g. by a
# test fixture or a second root), and THIS root still has only its old-name
# file. It must still be read, and adopted on the next write - not orphaned.
fresh
HOLD="$HM"
legacy boxa Linux "tw_bin: /real/tw
proof_run: run-real 2026-10-01 nf-core/demo"
REALCFG="$CFG"; REALMD="$MD"
fresh   # another root, same HOME: its write makes the id
HM="$HOLD"
run "$HM" boxa Linux -- bash "$SETTINGS" --set tw_bin /fixture/tw >/dev/null 2>&1
t "HIGH-1 precondition: an id now exists" "$(exists "$(IDF "$HM")")" "yes"
CFG="$REALCFG"; MD="$REALMD"
t "HIGH-1 real root's old file is still read" "$(run "$HM" boxa Linux -- bash "$SETTINGS" tw_bin)" "/real/tw"
out=$(run "$HM" boxa Linux -- bash "$PROOF" --check 2>&1); rc=$?
t "HIGH-1 real root's proof still counts" "$rc" "0"
run "$HM" boxa Linux -- bash "$SETTINGS" --set site_bridge wsl >/dev/null 2>&1
id="$(head -1 "$(IDF "$HM")" 2>/dev/null)"
t "HIGH-1 write adopts the old file: legacy name gone" "$(exists "$MD/boxa-Linux.yaml")" "no"
t "HIGH-1 old value kept in <id>.yaml" "$(grep -c '^tw_bin: /real/tw$' "$MD/$id.yaml" 2>/dev/null)" "1"
t "HIGH-1 exactly one machine file in the real root" "$(ls "$MD" | wc -l | tr -d ' ')" "1"

# --- acceptance M-2: rollback when the old file cannot be moved -------------
fresh
legacy boxa Linux "tw_bin: /old/tw"
chmod a-w "$MD"
if [ -w "$MD" ]; then
    printf '%-66s skipped (running as root: chmod cannot block mv)\n' "M-2 rollback"
else
    out=$(run "$HM" boxa Linux -- bash "$SETTINGS" --set site_bridge wsl 2>&1); rc=$?
    t "M-2 write fails when the old file cannot be renamed" "$([ "$rc" != 0 ] && echo yes)" "yes"
    t "M-2 the new id is rolled back" "$(exists "$(IDF "$HM")")" "no"
    t "M-2 the old value is still read" "$(run "$HM" boxa Linux -- bash "$SETTINGS" tw_bin)" "/old/tw"
fi
chmod u+w "$MD"

# --- acceptance M-2: an id file written with Windows line endings -----------
fresh
mkdir -p "$(dirname "$(IDF "$HM")")"; printf 'crid-1234\r\n' > "$(IDF "$HM")"
run "$HM" boxa Linux -- bash "$SETTINGS" --set tw_bin /cr/tw >/dev/null 2>&1
t "M-2 CRLF id file: machine file is crid-1234.yaml" "$(exists "$MD/crid-1234.yaml")" "yes"

# --- TC-006: Git Bash build number moved on ---------------------------------
fresh; legacy boxa MINGW64_NT-10.0-26100 "tw_bin: /win/tw"
t "TC-006 older build number still found" \
  "$(run "$HM" boxa MINGW64_NT-10.0-26200 -- bash "$SETTINGS" tw_bin)" "/win/tw"
run "$HM" boxa MINGW64_NT-10.0-26200 -- bash "$SETTINGS" --set site_bridge none >/dev/null 2>&1
id="$(head -1 "$(IDF "$HM")" 2>/dev/null)"
t "TC-006 first write adopts it (renamed)" "$(exists "$MD/$id.yaml")" "yes"
t "TC-006 the old-build name is gone" "$(exists "$MD/boxa-MINGW64_NT-10.0-26100.yaml")" "no"

# --- TC-007: several build numbers, newest wins -----------------------------
fresh
legacy boxa MINGW64_NT-10.0-26100 "tw_bin: /win/first"
legacy boxa MINGW64_NT-10.0-22631 "tw_bin: /win/newest"
legacy boxa MINGW64_NT-10.0-19045 "tw_bin: /win/third"
touch -t 202401010000 "$MD/boxa-MINGW64_NT-10.0-26100.yaml"
touch -t 202601010000 "$MD/boxa-MINGW64_NT-10.0-22631.yaml"
touch -t 202501010000 "$MD/boxa-MINGW64_NT-10.0-19045.yaml"
t "TC-007 the most recently modified one" \
  "$(run "$HM" boxa MINGW64_NT-10.0-26200 -- bash "$SETTINGS" tw_bin)" "/win/newest"
# Same family only: an MSYS file is not a MINGW64 one.
fresh; legacy boxa MSYS_NT-10.0-26100 "tw_bin: /msys/tw"
t "TC-007 a different prefix (MSYS vs MINGW64) is not adopted" \
  "$(run "$HM" boxa MINGW64_NT-10.0-26200 -- bash "$SETTINGS" tw_bin)" ""
fresh; legacy boxa MSYS_NT-10.0-26100 "tw_bin: /msys/tw"
t "TC-007 MSYS family matches MSYS" \
  "$(run "$HM" boxa MSYS_NT-10.0-26200 -- bash "$SETTINGS" tw_bin)" "/msys/tw"

# --- TC-008: another host's file is not adopted -----------------------------
fresh; legacy otherbox MINGW64_NT-10.0-26100 "tw_bin: /theirs"
legacy otherbox Linux "tw_bin: /theirs-linux"
t "TC-008 MINGW: other host not adopted" \
  "$(run "$HM" boxa MINGW64_NT-10.0-26200 -- bash "$SETTINGS" tw_bin)" ""
t "TC-008 Linux: other host not adopted" \
  "$(run "$HM" boxa Linux -- bash "$SETTINGS" tw_bin)" ""
run "$HM" boxa Linux -- bash "$SETTINGS" --set tw_bin /mine >/dev/null 2>&1
t "TC-008 writing leaves the other host's file alone" "$(exists "$MD/otherbox-Linux.yaml")" "yes"
t "TC-008 and its content" "$(cat "$MD/otherbox-Linux.yaml")" "tw_bin: /theirs-linux"

# --- TC-009: build-number tolerance is Windows-only --------------------------
fresh; legacy boxa Darwin "tw_bin: /mac/tw"
t "TC-009 Linux does not adopt a -Darwin file" \
  "$(run "$HM" boxa Linux -- bash "$SETTINGS" tw_bin)" ""
fresh; legacy boxa Linux-5.15 "tw_bin: /lin/tw"
t "TC-009 Linux does not adopt a look-alike suffix" \
  "$(run "$HM" boxa Linux -- bash "$SETTINGS" tw_bin)" ""

# --- TC-010: two homes, one root, same host/system --------------------------
fresh
H2="$TMP/h$n-b"; mkdir -p "$H2"
printf '{"workflows":[{"workflow":{"id":"run-ok","runName":"x","projectName":"nf-core/demo","status":"SUCCEEDED","userName":"alice","submit":"%s"}}]}\n' \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$TMP/runs.json"
runs_one() { run "$1" boxa Linux -- env RUNS_LIST_FILE="$TMP/runs.json" bash "$PROOF" --record "${2:-run-ok}" 2>&1; }
runs_one "$HM" >/dev/null; rc1=$?
t "TC-010 first home records" "$rc1" "0"
chk() { run "$1" boxa Linux -- bash "$PROOF" --check 2>&1; }
t "TC-010 first home sees its own proof" "$(chk "$HM" >/dev/null; echo $?)" "0"
t "TC-010 second home sees none (not the first's)" "$(chk "$H2" >/dev/null; echo $?)" "1"
printf '{"workflows":[{"workflow":{"id":"run-two","runName":"x","projectName":"nf-core/demo","status":"SUCCEEDED","userName":"alice","submit":"%s"}}]}\n' \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$TMP/runs.json"
runs_one "$H2" run-two >/dev/null
t "TC-010 second home records" "$(chk "$H2" >/dev/null; echo $?)" "0"
t "TC-010 two different machine files" "$(ls "$MD" | wc -l | tr -d ' ')" "2"
t "TC-010 two different ids" \
  "$(cat "$(IDF "$HM")" "$(IDF "$H2")" | sort -u | wc -l | tr -d ' ')" "2"
has "TC-010 first still sees run-ok" "run-ok" "$(chk "$HM")"
has "TC-010 second sees run-two" "run-two" "$(chk "$H2")"

# --- TC-011: a damaged id file is not used -----------------------------------
long="$(printf 'a%.0s' $(seq 1 65))"
for bad in "" "   " "../../etc/x" "$long" "a b" "bad/slash"; do
    fresh; mkdir -p "$(dirname "$(IDF "$HM")")"
    printf '%s\n' "$bad" > "$(IDF "$HM")"
    label="$(printf '%s' "$bad" | cut -c1-12)"
    out=$(run "$HM" boxa Linux -- bash "$SETTINGS" --set tw_bin /x/tw 2>&1); rc=$?
    nid="$(head -1 "$(IDF "$HM")")"
    t "TC-011 [$label] write succeeds" "$rc" "0"
    t "TC-011 [$label] a new valid id replaced it" "$(printf '%s' "$nid" | grep -cE '^boxa-[0-9a-f]{8}$')" "1"
    has "TC-011 [$label] stderr says the old one was not used" "machine-id" "$out"
    t "TC-011 [$label] everything stays inside machines/" \
      "$(find "$TMP/c$n" -type f | grep -vcE "^$MD/[^/]*$|/env.yaml$")" "0"
    t "TC-011 [$label] machine file is <new id>.yaml" "$(exists "$MD/$nid.yaml")" "yes"
done
# a damaged id file must not be used for reading either
fresh; mkdir -p "$(dirname "$(IDF "$HM")")"; printf '../../etc/x\n' > "$(IDF "$HM")"
legacy boxa Linux "tw_bin: /old/tw"
t "TC-011 reading with a damaged id falls back to legacy" \
  "$(run "$HM" boxa Linux -- bash "$SETTINGS" tw_bin)" "/old/tw"

# --- TC-012: the id cannot be saved ------------------------------------------
# A plain file where the config folder should be: mkdir -p fails for every user,
# root included (a chmod-readonly folder would not stop root).
fresh; mkdir -p "$HM/.config"; : > "$HM/.config/agentic-bioflow"
out=$(run "$HM" boxa Linux -- bash "$SETTINGS" --set tw_bin /x/tw 2>&1); rc=$?
t "TC-012 exits non-zero" "$([ "$rc" != 0 ] && echo yes)" "yes"
has "TC-012 says what could not be written" "machine-id" "$out"
t "TC-012 no machines dir was created" "$(exists "$MD")" "no"
t "TC-012 no hostname-system machine file" "$(exists "$MD/boxa-Linux.yaml")" "no"
# and a legacy file is left exactly as it was
fresh; mkdir -p "$HM/.config"; : > "$HM/.config/agentic-bioflow"; legacy boxa Linux "tw_bin: /old/tw"
run "$HM" boxa Linux -- bash "$SETTINGS" --set tw_bin /x/tw >/dev/null 2>&1
t "TC-012 legacy file untouched" "$(cat "$MD/boxa-Linux.yaml")" "tw_bin: /old/tw"

# --- TC-013: docs and printed paths ------------------------------------------
fresh
run "$HM" boxa Linux -- bash "$SETTINGS" --set tw_bin /x/tw >/dev/null 2>&1
id="$(head -1 "$(IDF "$HM")")"
t "TC-013 fixture has a valid id" "$(printf "%s" "$id" | grep -cE "^boxa-[0-9a-f]{8}$")" "1"
t "TC-013 --machine-file prints <id>.yaml" \
  "$(run "$HM" boxa Linux -- bash "$SETTINGS" --machine-file)" "$MD/$id.yaml"
has "TC-013 where.sh prints <id>.yaml" "$id.yaml" "$(run "$HM" boxa Linux -- bash "$WHERE" 2>&1)"
has "TC-013 --summary prints <id>.yaml" "$id.yaml" "$(run "$HM" boxa Linux -- bash "$SETTINGS" --summary 2>&1)"
SD="$ROOT/docs/SETTINGS.md"
dc() { grep -cF -- "$1" "$SD"; }
t "TC-013 SETTINGS.md names the id file" "$([ "$(dc "agentic-bioflow/machine-id")" -ge 1 ] && echo yes)" "yes"
t "TC-013 SETTINGS.md says the id has a random suffix" "$([ "$(dc "random suffix")" -ge 1 ] && echo yes)" "yes"
t "TC-013 old rule is gone" "$(dc 'The machine id is `<hostname>-<uname -s>`')" "0"
t "TC-013 SETTINGS.md explains the one-time rename" "$([ "$(dc "renamed")" -ge 1 ] && echo yes)" "yes"

echo
[ "$fails" = 0 ] && { echo "all machine-identity checks passed"; exit 0; }
echo "$fails check(s) failed"; exit 1
