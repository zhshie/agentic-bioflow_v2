#!/bin/bash
# fetch.sh brought results back; nothing carried data the other way, and
# launch.md simply asserted "the reads are on the site". For anyone whose own
# raw data has never left their laptop that is not guidance, it is a dead end -
# and it is the ordinary case, not the exotic one.
#
# push.sh is the mirror image, with one asymmetry that matters: there is no
# size cap. Raw reads are legitimately tens of gigabytes and moving them is the
# whole point, so the size is reported rather than refused.
P="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/scripts/push.sh"
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
fails=0
settings() { printf '%s\n' "$@" > "$TMP/env.yaml"; }
printf '#!/bin/bash\nexit 0\n' > "$TMP/rsync"; chmod +x "$TMP/rsync"
printf '#!/bin/bash\nexit 0\n' > "$TMP/ssh";   chmod +x "$TMP/ssh"
mkdir -p "$TMP/reads"; head -c 2048 /dev/zero > "$TMP/reads/a.fastq.gz"

run() {
  LAB_SETTINGS_FILE="$TMP/env.yaml" ON_SITE_SSH_BIN="$TMP/ssh" \
  PUSH_RSYNC_BIN="$TMP/rsync" bash "$P" "$@" 2>&1
}
t() { # t <label> <expect-rc> <expect-substring> -- <args...>
  local label="$1" want_rc="$2" want="$3"; shift 4
  printf '%-58s ' "$label"
  local out rc; out=$(run "$@"); rc=$?
  if [ "$rc" != "$want_rc" ]; then echo "FAIL: rc $rc wanted $want_rc <<$out>>"; fails=$((fails+1)); return; fi
  if [ -n "$want" ] && ! grep -qF -- "$want" <<<"$out"; then echo "FAIL: lacks '$want' <<$out>>"; fails=$((fails+1)); return; fi
  echo ok
}

D=/work/runs/myrun/rawdata

# Already on the site: there is nothing to move, and saying so beats copying
# 40 GB from one directory to another on the same filesystem.
settings 'reach: local'
t "local answers with the path itself"       0 "$TMP/reads"    -- "$TMP/reads" "$D"

settings 'reach: none' 'storage_root: s3://b/runs'
t "none refuses rather than guessing"        2 "object storage" -- "$TMP/reads" "$D"

settings 'reach: ssh' 'site_host: me@example.org'
t "ssh reports both ends and the size"       0 "$D"            -- --dry-run "$TMP/reads" "$D"
t "and says how much is about to move"       0 "KB"            -- --dry-run "$TMP/reads" "$D"
t "a real push answers with the site path"   0 "$D"            -- "$TMP/reads" "$D"

# The two ways a caller gets this wrong, both of which used to be an rsync
# error from three layers down.
t "a source that does not exist is caught"   2 "does not exist" -- "$TMP/nope" "$D"
t "and a missing destination is refused"     2 "usage"          -- "$TMP/reads"

# --- no rsync on PATH: falls back to tar|ssh instead of hard-failing --------
# Issue #6: Git Bash ships no rsync by default. PUSH_RSYNC_BIN pointed at a
# path that does not exist is this file's own existing override mechanism,
# repurposed to simulate that - `command -v` on it fails exactly like a bare
# `rsync` would on a PATH with none installed.
#
# The stub ssh logs every call it receives (so the remote command string can
# be inspected afterward) and, when that command is the tar|ssh fallback's
# own extraction (recognised by "tar xzf" in argv), drains stdin so the real
# local `tar czf` on the other end of the pipe completes rather than hitting
# a broken pipe on a stub that never reads.
SSHLOG="$TMP/ssh_push.log"
mktar_fallback_ssh() {
  : > "$SSHLOG"
  cat > "$TMP/ssh" <<EOF
#!/bin/bash
printf '%s\n' "\$*" >> "$SSHLOG"
last="\${@: -1}"
case "\$last" in
  *"tar xzf"*) cat > /dev/null ;;
esac
exit 0
EOF
  chmod +x "$TMP/ssh"
}

settings 'reach: ssh' 'site_host: me@example.org'

# A directory push - the shape the rsync-backed tests above already exercise.
mktar_fallback_ssh
out=$(LAB_SETTINGS_FILE="$TMP/env.yaml" ON_SITE_SSH_BIN="$TMP/ssh" \
      PUSH_RSYNC_BIN="$TMP/no-such-rsync" bash "$P" "$TMP/reads" "$D" 2>&1); rc=$?
printf '%-58s ' "no rsync, directory push: falls back instead of hard-failing"
[ "$rc" = 0 ] && echo ok || { echo "FAIL: rc $rc <<$out>>"; fails=$((fails+1)); }
printf '%-58s ' "and the tar|ssh fallback actually extracted remotely"
grep -qF "tar xzf" "$SSHLOG" && echo ok || { echo "FAIL: no tar xzf call logged: $(cat "$SSHLOG")"; fails=$((fails+1)); }

# A single-file push whose destination basename differs from the source's -
# the case rsync gets for free from an explicit target path, and the tar
# fallback has to ask the far side to rename after extracting.
mktar_fallback_ssh
DF="/work/runs/myrun/renamed.fastq.gz"
out=$(LAB_SETTINGS_FILE="$TMP/env.yaml" ON_SITE_SSH_BIN="$TMP/ssh" \
      PUSH_RSYNC_BIN="$TMP/no-such-rsync" bash "$P" "$TMP/reads/a.fastq.gz" "$DF" 2>&1); rc=$?
printf '%-58s ' "no rsync, file push: falls back instead of hard-failing"
[ "$rc" = 0 ] && echo ok || { echo "FAIL: rc $rc <<$out>>"; fails=$((fails+1)); }
printf '%-58s ' "and renames on the far side to match the destination name"
grep -qF "mv -f --" "$SSHLOG" && echo ok || { echo "FAIL: no rename logged: $(cat "$SSHLOG")"; fails=$((fails+1)); }

# Same basename both ends: no rename needed, and none should be attempted.
mktar_fallback_ssh
out=$(LAB_SETTINGS_FILE="$TMP/env.yaml" ON_SITE_SSH_BIN="$TMP/ssh" \
      PUSH_RSYNC_BIN="$TMP/no-such-rsync" bash "$P" "$TMP/reads/a.fastq.gz" "$D/a.fastq.gz" 2>&1); rc=$?
printf '%-58s ' "matching basenames: no rename is attempted"
[ "$rc" = 0 ] && ! grep -qF "mv -f --" "$SSHLOG" && echo ok \
  || { echo "FAIL: rc=$rc log=<<$(cat "$SSHLOG")>>"; fails=$((fails+1)); }

echo
[ "$fails" = 0 ] && echo "all passed" || { echo "$fails failed"; exit 1; }
