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

echo
[ "$fails" = 0 ] && echo "all passed" || { echo "$fails failed"; exit 1; }
