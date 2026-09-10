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

echo
[ "$fails" = 0 ] && echo "all passed" || { echo "$fails failed"; exit 1; }
