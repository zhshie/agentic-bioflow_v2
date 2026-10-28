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

# --- drive-letter local sources are never handed to rsync as-is --------------
# C:/x or C:\x has the shape rsync reads as host:path (a remote end). push.sh
# converts the local source to the MSYS form (/c/x) for rsync only; the remote
# end is untouched. (Cause inferred from rsync's host:path rule; not reproduced
# on Windows.) Relative folders literally named "C:" make this testable on
# Linux/WSL only.
case "$(uname -s)" in
  MINGW*|MSYS*|CYGWIN*)
    echo "note: drive-letter assertions run on Linux/WSL only" ;;
  *)
    settings 'reach: ssh' 'site_host: me@example.org'
    ARGS="$TMP/rsync.args"
    printf '#!/bin/bash\nprintf "%%s\\n" "$@" > "%s"\nexit "${REC_RC:-0}"\n' "$ARGS" > "$TMP/rsync_rec"
    chmod +x "$TMP/rsync_rec"
    printf '#!/bin/bash\nexit 0\n' > "$TMP/ssh"; chmod +x "$TMP/ssh"
    mkdir -p "$TMP/C:/Users/me/reads" "$TMP/C:\\Users\\me\\reads" "$TMP/\\\\server\\share\\reads" "$TMP/rd"
    head -c 2048 /dev/zero > "$TMP/C:/Users/me/reads/a.fastq.gz"
    head -c 2048 /dev/zero > "$TMP/C:\\Users\\me\\reads/a.fastq.gz"
    head -c 2048 /dev/zero > "$TMP/\\\\server\\share\\reads/a.fastq.gz"
    head -c 2048 /dev/zero > "$TMP/C:/Users/me/a.fastq.gz"
    prun() { # prun <args...>: run in $TMP with the recording rsync; sets OUT, RC
      rm -f "$ARGS"
      OUT=$(cd "$TMP" && LAB_SETTINGS_FILE="$TMP/env.yaml" ON_SITE_SSH_BIN="$TMP/ssh" \
            PUSH_RSYNC_BIN="$TMP/rsync_rec" bash "$P" "$@" 2>&1); RC=$?
    }
    srcarg()  { tail -n 2 "$ARGS" 2>/dev/null | head -n 1; }
    destarg() { tail -n 1 "$ARGS" 2>/dev/null; }
    chk() { # chk <label> <rc of the condition> [detail]
      printf '%-58s ' "$1"
      if [ "$2" = 0 ]; then echo ok; else echo "FAIL: ${3:-}"; fi
      [ "$2" = 0 ] || fails=$((fails+1))
    }
    src_is() { # src_is <TC> <local-src> <expected source arg> <remote dst> <expected last arg>
      prun "$2" "$4"
      [ "$RC" = 0 ] && [ "$(srcarg)" = "$3" ] && [ "$(destarg)" = "$5" ]
      chk "$1 $2 -> rsync gets $3" $? "rc=$RC src=<<$(srcarg)>> dst=<<$(destarg)>> out=<<$OUT>>"
    }
    HD="me@example.org:$D/"
    src_is "TC-015/016" 'C:/Users/me/reads' '/c/Users/me/reads/' "$D" "$HD"
    src_is "TC-017" 'C:/Users/me/a.fastq.gz' '/c/Users/me/a.fastq.gz' "$D/a.fastq.gz" "me@example.org:$D/a.fastq.gz"
    src_is "TC-018" 'C:\Users\me\reads' '/c/Users/me/reads/' "$D" "$HD"
    src_is "TC-019" "$TMP/reads" "$TMP/reads/" "$D" "$HD"
    src_is "TC-020" "$TMP/reads/a.fastq.gz" "$TMP/reads/a.fastq.gz" "$D/a.fastq.gz" "me@example.org:$D/a.fastq.gz"
    src_is "TC-029" '\\server\share\reads' '\\server\share\reads/' "$D" "$HD"

    # TC-021: --dry-run output unchanged, rsync not called.
    prun --dry-run 'C:/Users/me/reads' "$D"
    [ "$RC" = 0 ] && grep -qF 'C:/Users/me/reads' <<<"$OUT" \
      && grep -qF "ssh me@example.org:$D" <<<"$OUT" && ! grep -qF '/c/Users' <<<"$OUT" \
      && [ ! -s "$ARGS" ]
    chk "TC-021 --dry-run shows the original path" $? "rc=$RC <<$OUT>>"

    # TC-022: stdout is still the site path.
    prun 'C:/Users/me/reads' "$D"
    [ "$RC" = 0 ] && [ "$(tail -n 1 <<<"$OUT")" = "$D" ]
    chk "TC-022 stdout is the site path" $? "<<$OUT>>"

    # TC-023: failure message and exit code unchanged.
    REC_RC=1 prun 'C:/Users/me/reads' "$D"
    [ "$RC" = 2 ] && grep -qF "the transfer of 'C:/Users/me/reads' failed." <<<"$OUT" \
      && grep -qF -- '--partial' <<<"$OUT"
    chk "TC-023 failed transfer: rc 2, same message" $? "rc=$RC <<$OUT>>"

    # TC-024: the existence check runs on the user's own path, before conversion.
    prun 'C:/Users/me/nope' "$D"
    [ "$RC" = 2 ] && grep -qF "'C:/Users/me/nope' does not exist on this machine." <<<"$OUT" \
      && [ ! -s "$ARGS" ]
    chk "TC-024 missing source reported as given" $? "rc=$RC <<$OUT>>"

    # TC-028: never the WSL /mnt/ form.
    prun 'C:/Users/me/reads' "$D"
    ! grep -qF '/mnt/' "$ARGS"
    chk "TC-028 no /mnt/ form is produced" $? "<<$(cat "$ARGS" 2>/dev/null)>>"

    # TC-027: the tar|ssh fallback is untouched and reads the original folder.
    mktar_fallback_ssh
    OUT=$(cd "$TMP" && LAB_SETTINGS_FILE="$TMP/env.yaml" ON_SITE_SSH_BIN="$TMP/ssh" \
          PUSH_RSYNC_BIN="$TMP/no-such-rsync" bash "$P" 'C:/Users/me/reads' "$D" 2>&1); RC=$?
    [ "$RC" = 0 ] && grep -qF "mkdir -p $D && tar xzf - -C $D" "$SSHLOG"
    chk "TC-027 tar fallback keeps the original path" $? "rc=$RC log=<<$(cat "$SSHLOG")>>" ;;
esac

echo
[ "$fails" = 0 ] && echo "all passed" || { echo "$fails failed"; exit 1; }
