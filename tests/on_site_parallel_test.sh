#!/bin/bash
# N9-2: scripts/on_site.sh caps concurrent ssh sessions per master (PITFALLS
# 16e - past sshd's MaxSessions, the next session-open hangs rather than
# errors, and the risk grows with several lab agents sharing one master,
# docs/LAB_AGENTS.md). tests/on_site_test.sh covers the N9-1/N9-3 additions
# and that local/none never touch the slot machinery at all; this file covers
# what needs real contention or a real signal to see: the cap itself, release
# on every exit shape, staleness reclaim, and the wait-until-timeout path.
#
# Split out per CLAUDE.md's own suggestion ("a new
# tests/on_site_parallel_test.sh if cleaner") - these cases are slower and
# shaped differently (background jobs, signals, timing) from the rest of
# tests/on_site_test.sh's fast substring checks, and mixing them in would slow
# down every run of that file for a concern only this one has.
#
# Only the first block runs through ON_SITE_DRY_RUN=1 - that is the specific
# seam CLAUDE.md says these tests use, and on_site.sh's dry-run path still
# acquires and releases a real slot for it (see scripts/on_site.sh, the
# ON_SITE_DRY_RUN block: it only ever calls the configured ssh binary when
# ON_SITE_SSH_BIN is set, which a real deployment never does - it is named
# "(tests)" in the script's own header and nothing outside tests/ sets it).
# The rest run the real command path with a fake ssh substituted for
# ON_SITE_SSH_BIN, the same way tests/on_site_test.sh's tt() already does -
# no dry run needed once the point is real contention over the slot files.
# Neither shape ever opens a real ssh connection.
set -uo pipefail
S="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/scripts/on_site.sh"
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
fails=0
settings() { printf '%s\n' "$@" > "$TMP/env.yaml"; }
settings 'reach: ssh' 'site_host: me@example.org' "ssh_control_path: $TMP/cm"
SLOTS="$TMP/cm.slots"

slots_held() { [ -d "$SLOTS" ] && find "$SLOTS" -mindepth 1 -maxdepth 1 2>/dev/null | grep -q .; }

# ---------------------------------------------------------------------------
# At most ON_SITE_MAX_PARALLEL sessions run at once, and a caller past the cap
# waits rather than running unbounded - through the ON_SITE_DRY_RUN seam.
# ---------------------------------------------------------------------------
# A fake ssh that holds its slot for ~1s and records, via its own mkdir-lock,
# the largest number of copies of itself ever running at the same time.
LOCK="$TMP/counter.lock"; CNT="$TMP/count"; SEEN="$TMP/maxseen"
printf '0\n' > "$CNT"; printf '0\n' > "$SEEN"
cat > "$TMP/fake-ssh-slots" <<EOF
#!/bin/bash
for a in "\$@"; do [ "\$a" = check ] && exit 0; done
while ! mkdir "$LOCK" 2>/dev/null; do sleep 0.02; done
c=\$(cat "$CNT"); c=\$((c + 1)); printf '%s\n' "\$c" > "$CNT"
m=\$(cat "$SEEN"); [ "\$c" -gt "\$m" ] && printf '%s\n' "\$c" > "$SEEN"
rmdir "$LOCK"
sleep 1
while ! mkdir "$LOCK" 2>/dev/null; do sleep 0.02; done
c=\$(cat "$CNT"); c=\$((c - 1)); printf '%s\n' "\$c" > "$CNT"
rmdir "$LOCK"
EOF
chmod +x "$TMP/fake-ssh-slots"

start=$(date +%s)
for i in 1 2 3; do
  ( LAB_SETTINGS_FILE="$TMP/env.yaml" ON_SITE_DRY_RUN=1 \
    ON_SITE_SSH_BIN="$TMP/fake-ssh-slots" ON_SITE_MAX_PARALLEL=2 ON_SITE_TIMEOUT=10 \
    bash "$S" true > "$TMP/out.$i" 2>&1 ) &
done
wait
elapsed=$(( $(date +%s) - start ))

printf '%-58s ' "at most 2 fake sessions ran at once (cap respected)"
seen=$(cat "$SEEN")
if [ "$seen" -ge 1 ] && [ "$seen" -le 2 ]; then echo "ok (saw $seen)"
else echo "FAIL: saw $seen concurrent"; fails=$((fails+1)); fi

printf '%-58s ' "the cap was genuinely exercised (2 did overlap)"
[ "$seen" = 2 ] && echo ok \
  || { echo "FAIL: never saw 2 at once (saw $seen) - not a real concurrency test"; fails=$((fails+1)); }

printf '%-58s ' "all three dry-run callers completed"
ok3=1
for i in 1 2 3; do grep -q "ssh me@example.org" "$TMP/out.$i" || ok3=0; done
[ "$ok3" = 1 ] && echo ok || { echo "FAIL"; fails=$((fails+1)); }

printf '%-58s ' "the third completed only after one freed, not immediately"
# 2 together for ~1s, then the third for ~1s more: ~2s. ~1s would mean the
# cap did nothing; a much longer time would mean they ran fully serial.
if [ "$elapsed" -ge 2 ] && [ "$elapsed" -le 6 ]; then echo "ok (${elapsed}s)"
else echo "FAIL: took ${elapsed}s"; fails=$((fails+1)); fi

printf '%-58s ' "and every slot was released afterwards"
slots_held && { echo "FAIL: a slot dir is still held"; fails=$((fails+1)); } || echo ok

# ---------------------------------------------------------------------------
# Release on every exit shape, over the real (non-dry) command path.
# ---------------------------------------------------------------------------
mkecho() { printf '#!/bin/bash\nfor a in "$@"; do [ "$a" = check ] && exit 0; done\n%s\n' "$1" > "$TMP/fake-ssh"; chmod +x "$TMP/fake-ssh"; }
run_real() { LAB_SETTINGS_FILE="$TMP/env.yaml" ON_SITE_SSH_BIN="$TMP/fake-ssh" ON_SITE_MAX_PARALLEL=1 bash "$S" true; }

rm -rf "$SLOTS"; mkecho "exit 0"
run_real >/dev/null 2>&1; rc=$?
printf '%-58s ' "slot freed after a normal (successful) exit"
if [ "$rc" = 0 ] && ! slots_held; then echo ok
else echo "FAIL: rc=$rc, held=$(slots_held && echo yes || echo no)"; fails=$((fails+1)); fi

rm -rf "$SLOTS"; mkecho "exit 1"
run_real >/dev/null 2>&1; rc=$?
printf '%-58s ' "slot freed after a failing (non-hanging) command"
if [ "$rc" = 1 ] && ! slots_held; then echo ok
else echo "FAIL: rc=$rc, held=$(slots_held && echo yes || echo no)"; fails=$((fails+1)); fi

rm -rf "$SLOTS"
printf '#!/bin/bash\nfor a in "$@"; do [ "$a" = check ] && exit 0; done\nsleep 30\n' > "$TMP/fake-ssh"
chmod +x "$TMP/fake-ssh"
LAB_SETTINGS_FILE="$TMP/env.yaml" ON_SITE_SSH_BIN="$TMP/fake-ssh" ON_SITE_MAX_PARALLEL=1 \
  ON_SITE_TIMEOUT=25 bash "$S" true >/dev/null 2>&1 &
bgpid=$!
waited=0
while [ ! -d "$SLOTS/1" ] && [ "$waited" -lt 20 ]; do sleep 0.2; waited=$((waited+1)); done
printf '%-58s ' "(setup) the slot was actually held before the signal"
[ -d "$SLOTS/1" ] && echo ok || { echo "FAIL: slot never appeared"; fails=$((fails+1)); }
kill -TERM "$bgpid" 2>/dev/null
wait "$bgpid" 2>/dev/null
# The fake ssh's own sleep is a separate process the signal was never aimed
# at; on_site.sh's job is to release the slot, not to reach in and kill it.
pkill -TERM -f "$TMP/fake-ssh" 2>/dev/null || true
waited=0
while slots_held && [ "$waited" -lt 20 ]; do sleep 0.2; waited=$((waited+1)); done
printf '%-58s ' "slot freed after SIGTERM to the waiting on_site.sh"
slots_held && { echo "FAIL: slot dir survived the signal"; fails=$((fails+1)); } || echo ok

# ---------------------------------------------------------------------------
# A stale slot (holder's pid is dead) is reclaimed rather than waited out.
# ---------------------------------------------------------------------------
rm -rf "$SLOTS"; mkdir -p "$SLOTS/1"
( : ) & deadpid=$!; wait "$deadpid" 2>/dev/null   # a pid guaranteed to be gone now
echo "$deadpid" > "$SLOTS/1/pid"
mkecho "exit 0"
start=$(date +%s)
out=$(run_real 2>&1); rc=$?
elapsed=$(( $(date +%s) - start ))
printf '%-58s ' "a stale slot (dead pid) is reclaimed, not waited out"
if [ "$rc" = 0 ] && [ "$elapsed" -le 3 ]; then echo ok
else echo "FAIL: rc=$rc after ${elapsed}s <<$out>>"; fails=$((fails+1)); fi

# ---------------------------------------------------------------------------
# No slot ever frees -> sessions-exhausted (N9-1's line), not an infinite wait.
# ---------------------------------------------------------------------------
rm -rf "$SLOTS"; mkdir -p "$SLOTS/1"
echo $$ > "$SLOTS/1/pid"   # this test script's own pid: alive for the duration
mkecho "exit 0"
start=$(date +%s)
out=$(LAB_SETTINGS_FILE="$TMP/env.yaml" ON_SITE_SSH_BIN="$TMP/fake-ssh" \
      ON_SITE_MAX_PARALLEL=1 ON_SITE_TIMEOUT=2 bash "$S" true 2>&1); rc=$?
elapsed=$(( $(date +%s) - start ))

printf '%-58s ' "no free slot before ON_SITE_TIMEOUT exits with an error"
[ "$rc" != 0 ] && echo "ok (rc=$rc)" || { echo "FAIL: rc=0"; fails=$((fails+1)); }

printf '%-58s ' "...carrying the sessions-exhausted needs-human line"
grep -qF "on_site: needs-human reason=sessions-exhausted host=me@example.org" <<<"$out" \
  && echo ok || { echo "FAIL: <<$out>>"; fails=$((fails+1)); }

printf '%-58s ' "...having actually waited, not returned immediately"
[ "$elapsed" -ge 1 ] && echo "ok (${elapsed}s)" || { echo "FAIL: returned after ${elapsed}s"; fails=$((fails+1)); }
rm -rf "$SLOTS"

echo
[ "$fails" = 0 ] && echo "all passed" || { echo "$fails failed"; exit 1; }
