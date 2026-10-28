#!/bin/bash
# scripts/fetch.sh brings a site path to where it can be read.
#
# The case worth testing is the one that costs money and time rather than the
# one that works: `work/` next to `results/` is three orders of magnitude
# larger, and a laptop asked to pull it over a home connection gives no sign of
# what it is doing for the first hour. So the size is asked for before anything
# moves, and the refusal has to name its own override.
#
# Everything runs through FETCH_DRY_RUN and stub binaries: no site, no network.
F="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/scripts/fetch.sh"
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
fails=0

settings() { printf '%s\n' "$@" > "$TMP/env.yaml"; }
# A stub ssh that reports whatever size the test wants the site to have.
# The argument is KILOBYTES: fetch.sh asks the site with `du -sk`, because the
# byte mode is GNU-only and that same command runs locally under reach:local.
mkssh() { printf '#!/bin/bash\necho "%s\t/x"\nexit 0\n' "$1" > "$TMP/ssh"; chmod +x "$TMP/ssh"; }

run() {
  LAB_SETTINGS_FILE="$TMP/env.yaml" ON_SITE_SSH_BIN="$TMP/ssh" \
  FETCH_ROOT="$TMP/stage" FETCH_RSYNC_BIN="$TMP/rsync" bash "$F" "$@" 2>&1
}
printf '#!/bin/bash\nexit 0\n' > "$TMP/rsync"; chmod +x "$TMP/rsync"

t() { # t <label> <expect-rc> <expect-substring> -- <args...>
  local label="$1" want_rc="$2" want="$3"; shift 4
  printf '%-58s ' "$label"
  local out rc; out=$(run "$@"); rc=$?
  if [ "$rc" != "$want_rc" ]; then echo "FAIL: rc $rc wanted $want_rc <<$out>>"; fails=$((fails+1)); return; fi
  if [ -n "$want" ] && ! grep -qF -- "$want" <<<"$out"; then echo "FAIL: lacks '$want' <<$out>>"; fails=$((fails+1)); return; fi
  echo ok
}

R=/work/runs/myrun/results

# On the site already: the answer is the path, and nothing is copied. Anything
# else would double 25 GB of results onto the same filesystem.
settings 'reach: local'
t "local answers with the path itself"        0 "$R"              -- "$R"
printf '%-58s ' "local copies nothing"
[ -e "$TMP/stage" ] && { echo "FAIL: made a staging dir"; fails=$((fails+1)); } || echo ok

# Object storage needs cloud credentials and a client this has never run
# against. Saying so is honest; guessing would be invariant 8.
settings 'reach: none' 'storage_root: s3://b/runs'
t "none refuses rather than guessing"         2 "object storage"  -- "$R"

settings 'reach: ssh' 'site_host: me@example.org'
mkssh 26000                                      # 26 MB - a real delivery
t "ssh reports where it would land"           0 "$TMP/stage"      -- --dry-run "$R"
t "and mirrors the site path under it"        0 "stage/work/runs/myrun/results" -- --dry-run "$R"
t "a real fetch prints the local path"        0 "stage/work/runs/myrun/results" -- "$R"

mkssh 90000000                                   # 90 GB - a work directory
t "an oversized path is refused"              2 "90"              -- "$R"
t "and the refusal names its override"        2 "--max-mb"        -- "$R"
# The override is the expensive answer, and it used to be the only one offered.
# This file's own header says why the size check exists: a laptop asked to pull
# a work directory over a home connection shows nothing for the first hour. So
# a refusal that names only --max-mb hands over the way to do exactly that.
# Measured against a real 10.9 GB results tree on 2026-09-09. docs/DOWNSTREAM.md
# already specifies the cheap answer - send the analysis to the site instead -
# and the refusal is where someone is standing when they need to hear it.
t "and the refusal names the cheaper route"   2 "on_site.sh"      -- "$R"
t "which then works"                          0 "stage/"          -- --max-mb 100000 "$R"

# --- no rsync on PATH: falls back to tar|ssh instead of hard-failing --------
# Issue #6: Git Bash ships no rsync by default. FETCH_RSYNC_BIN pointed at a
# path that does not exist is this file's own existing override mechanism,
# repurposed to simulate that - `command -v` on it fails exactly like a bare
# `rsync` would on a PATH with none installed.
#
# The stub ssh below distinguishes fetch.sh's two different uses of $SSH: the
# `du -sk` size probe (mkssh's ordinary reply) and the tar|ssh fallback's own
# remote command (recognised by the "tar czf" substring in argv). The latter
# answers with a real, valid empty gzip stream so the local `tar xzf -` on
# the other end of the pipe has something to extract without needing a real
# site - and records that it was reached at all, which is the thing under
# test: that the fallback path runs rather than the rsync stub ever being
# asked to.
mktar_fallback_ssh() {
  cat > "$TMP/ssh" <<EOF
#!/bin/bash
last="\${@: -1}"
case "\$last" in
  *"tar czf"*)
    : > "$TMP/tar_fallback_invoked"
    tar czf - -T /dev/null
    ;;
  *)
    printf '%s\t/x\n' "$1"
    ;;
esac
EOF
  chmod +x "$TMP/ssh"
}
mktar_fallback_ssh 26000
rm -f "$TMP/tar_fallback_invoked"
out=$(LAB_SETTINGS_FILE="$TMP/env.yaml" ON_SITE_SSH_BIN="$TMP/ssh" \
      FETCH_ROOT="$TMP/stage" FETCH_RSYNC_BIN="$TMP/no-such-rsync" \
      bash "$F" "$R" 2>&1); rc=$?
printf '%-58s ' "no rsync on PATH: falls back instead of hard-failing"
[ "$rc" = 0 ] && echo ok || { echo "FAIL: rc $rc <<$out>>"; fails=$((fails+1)); }
printf '%-58s ' "and the tar|ssh fallback actually ran"
[ -e "$TMP/tar_fallback_invoked" ] && echo ok || { echo "FAIL: fallback never invoked"; fails=$((fails+1)); }

# --- drive-letter local paths are never handed to rsync as-is ----------------
# A local path written C:/x or C:\x has the shape rsync reads as host:path, i.e.
# a remote end. fetch.sh converts it to the MSYS form (/c/x) for rsync only.
# (The cause is inferred from rsync's host:path rule; not reproduced on Windows.)
# The assertions use relative folders literally named "C:" and so run on
# Linux/WSL only.
case "$(uname -s)" in
  MINGW*|MSYS*|CYGWIN*)
    echo "note: drive-letter assertions run on Linux/WSL only" ;;
  *)
    settings 'reach: ssh' 'site_host: me@example.org'
    mkssh 26000
    ARGS="$TMP/rsync.args"
    printf '#!/bin/bash\nprintf "%%s\\n" "$@" > "%s"\nexit "${REC_RC:-0}"\n' "$ARGS" > "$TMP/rsync_rec"
    chmod +x "$TMP/rsync_rec"
    rrun() { # rrun <args...>: run in $TMP with the recording rsync; sets OUT, RC
      rm -f "$ARGS"
      OUT=$(cd "$TMP" && PATH="${STUBPATH:+$STUBPATH:}$PATH" LAB_SETTINGS_FILE="$TMP/env.yaml" \
            ON_SITE_SSH_BIN="$TMP/ssh" FETCH_ROOT="$TMP/stage" FETCH_RSYNC_BIN="$TMP/rsync_rec" \
            bash "$F" "$@" 2>&1); RC=$?
    }
    # Absolute destinations that cannot be created here (/c/..., //server/...):
    # a stub mkdir that does nothing lets fetch.sh get as far as rsync.
    mkdir -p "$TMP/nomk"; printf '#!/bin/bash\nexit 0\n' > "$TMP/nomk/mkdir"; chmod +x "$TMP/nomk/mkdir"
    lastarg() { tail -n 1 "$ARGS" 2>/dev/null; }
    chk() { # chk <label> <rc of the condition> [detail]
      printf '%-58s ' "$1"
      if [ "$2" = 0 ]; then echo ok; else echo "FAIL: ${3:-}"; fails=$((fails+1)); fi
    }
    dest_is() { # dest_is <TC> <local-dest> <expected last rsync arg>
      rrun "$R" "$2"
      [ "$RC" = 0 ] && [ "$(lastarg)" = "$3" ]
      chk "$1 $2 -> rsync gets $3" $? "rc=$RC last=<<$(lastarg)>> out=<<$OUT>>"
    }
    dest_is "TC-001" 'C:/Users/me/out/results' '/c/Users/me/out/'
    dest_is "TC-002" 'D:\data\out\results'     '/d/data/out/'
    STUBPATH="$TMP/nomk" dest_is "TC-003" '/tmp/x/results'        '/tmp/x/'
    dest_is "TC-004" 'rel/results'             'rel/'
    dest_is "TC-005" 'C:/results'              '/c/'
    dest_is "TC-006" 'C:\results'              '/c/'
    dest_is "TC-007" 'c:/Users/me/out/results' '/c/Users/me/out/'
    STUBPATH="$TMP/nomk" dest_is "TC-008" '/c/Users/me/out/results' '/c/Users/me/out/'
    dest_is "TC-009" './C:foo/results'         './C:foo/'
    STUBPATH="$TMP/nomk" dest_is "TC-030" '//server/share/out/results' "$(dirname '//server/share/out/results')/"

    # TC-010: the user sees their own path, not the converted one.
    rrun "$R" 'C:/Users/me/out/results'
    [ "$RC" = 0 ] && [ "$(tail -n 1 <<<"$OUT")" = 'C:/Users/me/out/results' ]
    chk "TC-010 stdout is the user's own path" $? "<<$OUT>>"

    # TC-011: --dry-run output unchanged, rsync not called.
    rrun --dry-run "$R" 'C:/Users/me/out/results'
    [ "$RC" = 0 ] && grep -qF 'C:/Users/me/out/results' <<<"$OUT" \
      && ! grep -qF '/c/Users' <<<"$OUT" && grep -qF 'ssh me@example.org' <<<"$OUT" \
      && grep -qF '(26 MB)' <<<"$OUT" && [ ! -s "$ARGS" ]
    chk "TC-011 --dry-run shows the original path" $? "rc=$RC <<$OUT>>"

    # TC-012: the remote end is never rewritten.
    rrun "$R" 'C:/Users/me/out/results'
    grep -qxF "me@example.org:$R" "$ARGS" 2>/dev/null
    chk "TC-012 remote end untouched" $? "<<$(cat "$ARGS" 2>/dev/null)>>"

    # TC-013: mkdir -p used the original path (a relative folder named C:).
    rrun "$R" 'C:/Users/me/out/results'
    [ "$RC" = 0 ] && [ -d "$TMP/C:/Users/me/out" ]
    chk "TC-013 mkdir used the user's own path" $? "rc=$RC <<$OUT>>"

    # TC-014: failure message and exit code unchanged.
    REC_RC=1 rrun "$R" 'C:/Users/me/out/results'
    [ "$RC" = 2 ] && grep -qF "the transfer of '$R' failed." <<<"$OUT"
    chk "TC-014 failed transfer: rc 2, same message" $? "rc=$RC <<$OUT>>"

    # TC-028: never the WSL /mnt/ form.
    rrun "$R" 'C:/Users/me/out/results'
    ! grep -qF '/mnt/' "$ARGS"
    chk "TC-028 no /mnt/ form is produced" $? "<<$(cat "$ARGS" 2>/dev/null)>>"

    # TC-026: the tar|ssh fallback is untouched and uses the original path.
    mktar_fallback_ssh 26000
    rm -f "$TMP/tar_fallback_invoked"
    OUT=$(cd "$TMP" && LAB_SETTINGS_FILE="$TMP/env.yaml" ON_SITE_SSH_BIN="$TMP/ssh" \
          FETCH_ROOT="$TMP/stage" FETCH_RSYNC_BIN="$TMP/no-such-rsync" \
          bash "$F" "$R" 'C:/Users/me/out/results' 2>&1); RC=$?
    [ "$RC" = 0 ] && [ -e "$TMP/tar_fallback_invoked" ] \
      && [ "$(tail -n 1 <<<"$OUT")" = 'C:/Users/me/out/results' ]
    chk "TC-026 tar fallback keeps the original path" $? "rc=$RC <<$OUT>>" ;;
esac

# TC-025: both scripts carry the same conversion function (and both have one).
fa=$(sed -n '/^rsync_local_path()/,/^}/p' "$(dirname "$F")/fetch.sh")
pa=$(sed -n '/^rsync_local_path()/,/^}/p' "$(dirname "$F")/push.sh")
printf '%-58s ' "TC-025 fetch.sh and push.sh convert the same way"
if [ -n "$fa" ] && [ "$fa" = "$pa" ]; then echo ok; else echo "FAIL: functions differ or are missing"; fails=$((fails+1)); fi

echo
[ "$fails" = 0 ] && echo "all passed" || { echo "$fails failed"; exit 1; }
